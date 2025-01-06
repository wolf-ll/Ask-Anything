TextEncoders = dict()
TextEncoders["bert"] = dict(
    name="bert_base",
    pretrained="/home/bailey/Code/wyf/Ask-Anything/video_chat2/tasks/bert-base-uncased/",
    config="configs/config_bert.json",
    d_model=768,
    fusion_layer=9,
)