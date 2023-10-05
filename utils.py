def get_string_of_model(model_class):
    model_name = model_class.__name__
    # remove "Orm" postfix from model name
    model_name = model_name[:-3]
    model_name = model_name.lower()
    return model_name
