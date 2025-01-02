import logging
import os
import json
import random
import torch

import numpy as np

from dataset.base_dataset import ImageVideoBaseDataset
from dataset.video_utils import VIDEO_READER_FUNCS

logger = logging.getLogger(__name__)


class ITImgTrainDataset_phi(ImageVideoBaseDataset):
    media_type = "image"

    def __init__(
        self, ann_file, transform, 
        system="", 
        start_token="<Image>", end_token="</Image>",
        random_shuffle=False, # if True, shuffle the QA list
        return_question_instruction=False, # if True, return instruction with instruciton
    ):
        super().__init__()

        if len(ann_file) >= 3 and ann_file[2] == "video":
            self.media_type = "video"  
        else:
            self.media_type = "image"
        self.label_file, self.data_root = ann_file[:2]

        logger.info('Load json file')
        with open(self.label_file, 'r') as f:
            self.anno = json.load(f)
        self.num_examples = len(self.anno)
        self.transform = transform

        # prompt parameters
        if system:
            assert system[-1] == " ", "' ' should be add in the end of system."

        self.human_start = "<|user|>\n"
        self.human_end = "<|end|>\n<|assistant|>\n"
        self.assist_end = "<|end|>\n"
        self.start_token = start_token
        self.end_token = end_token
        self.system = system
        self.random_shuffle = random_shuffle
        # instruction location and number
        self.return_question_instruction = return_question_instruction
        logger.info(f"Random shuffle: {self.random_shuffle}")
        logger.info(f"Return question with instruction: {self.return_question_instruction}")

    def get_anno(self, index):
        filename = self.anno[index][self.media_type]
        qa = self.anno[index]["QA"]
        if "start" in self.anno[index] and "end" in self.anno[index]:
            anno = {
                "image": os.path.join(self.data_root, filename), "qa": qa,
                "start": self.anno[index]["start"], "end": self.anno[index]["end"],
            }
        else:
            anno = {"image": os.path.join(self.data_root, filename), "qa": qa}
        return anno

    def __len__(self):
        return self.num_examples
    
    def process_qa(self, qa, msg=""):
        cur_instruction = ""
        # randomly shuffle qa for conversation
        if self.random_shuffle and len(qa) > 1:
            random.shuffle(qa)
        if "i" in qa[0].keys() and qa[0]["i"] != "":
            cur_instruction = qa[0]["i"]

        conversation = self.system
        # add instruction as system message
        if cur_instruction:
            conversation += cur_instruction

        # add system token
        if conversation != "":
            conversation = f"<|system|>\n{conversation}<|end|>\n"

        for idx, sentence in enumerate(qa):
            q = sentence["q"]
            a = sentence["a"]
            if idx == 0:
                if q != "":
                    conversation += (self.human_start + self.start_token + self.end_token + msg.rstrip() + "\n" + q.strip() + self.human_end)
                else:
                    # no question, often in caption dataset
                    conversation += (self.human_start + self.start_token + self.end_token + msg.rstrip() + "\n" + self.human_end)
            else:
                conversation += (self.human_start + q.strip() + self.human_end)
            conversation += (a.strip() + self.assist_end)
        
        if self.return_question_instruction and cur_instruction:
            cur_instruction += qa[0]["q"]
        return conversation.strip(), cur_instruction.strip()

    def __getitem__(self, index):
        try:
            ann = self.get_anno(index)
            image, index = self.load_and_transform_media_data_image(
                index, ann["image"],
            )
            conversation, instruction = self.process_qa(ann["qa"])
            return image, conversation, instruction, index
        except Exception as e:
            logger.warning(f"Caught exception {e} when loading image {ann['image']}")
            index = np.random.randint(0, len(self))
            return self.__getitem__(index)


class ITVidTrainDataset_phi(ITImgTrainDataset_phi):
    media_type = "video"

    def __init__(
        self, ann_file, transform,
        num_frames=4, video_reader_type="decord", sample_type="rand", num_tries=3,
        system="", start_token="<Video>", end_token="</Video>",
        add_second_msg=False,
        random_shuffle=False,
        return_question_instruction=False, # if True, return instruction with instruciton
    ):
        super().__init__(
            ann_file, transform, 
            system=system,
            start_token=start_token, end_token=end_token,
            random_shuffle=random_shuffle,
            return_question_instruction=return_question_instruction,
        )
        self.num_frames = num_frames
        self.video_reader_type = video_reader_type
        self.video_reader = VIDEO_READER_FUNCS[video_reader_type]
        self.sample_type = sample_type
        self.num_tries = num_tries
        self.add_second_msg = add_second_msg

        logger.info(f"Use {video_reader_type} for data in {ann_file}")
        if add_second_msg:
            logger.info(f"Add second message: The video contains X frames sampled at T seconds.")

    def __getitem__(self, index):
        try:
            ann = self.get_anno(index)
            msg = ""
            clip = None
            if "start" in ann and "end" in ann:
                clip = [ann["start"], ann["end"]]
            video, index, sec = self.load_and_transform_media_data_video(
                index, ann["image"], return_fps=True, clip=clip,
            )
            if self.add_second_msg and sec is not None:
                # " " should be added in the start and end
                msg = f" The video contains {len(sec)} frames sampled at {', '.join(sec)} seconds. "
            conversation, instruction = self.process_qa(ann["qa"], msg)
            return video, conversation, instruction, index
        except Exception as e:
            logger.warning(f"Caught exception {e} when loading video {ann['image']}")
            index = np.random.randint(0, len(self))
            return self.__getitem__(index)

