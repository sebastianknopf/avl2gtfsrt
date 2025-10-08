def get_tls_value(topic: str, key: str, fail_on_error: bool = True) -> str|None:
    topic_components: list[str] = topic.split('/')
    if key in topic_components:
        result: str = topic_components[topic_components.index(key) + 1]

        return result
    else:
        if fail_on_error:
            raise LookupError(f"Key {key} not found in topic {topic}")
    
    return None