class IntegerCamProp:
    def __init__(self, name, min, max, default, value, step):
        self.min = min
        self.max = max
        self.default = default
        self.value = value
        self.step = step
        self.name = name
        self.new_value = value


def parse_int_props(propstr):
    proplist = []
    for line in propstr.splitlines():  # I don't even regex, so this will be fun
        if '(int)' in line:  # We have an integer attribute
            line = line.strip()
            words = line.split(' ')
            name = words[0]

            # Dedup
            exists = False
            for p in proplist:
                if p.name == name:
                    exists = True
            if exists:
                continue

            min = None
            max = None
            default = None
            value = None
            step = None
            for word in words:
                equals_split = word.split('=')
                if len(equals_split) > 1:  # We have a value
                    # We're talking about an attribute here, not the value itself
                    attr_name = equals_split[0].strip()
                    attr_value = equals_split[1]

                    if attr_name == "min":
                        min = int(attr_value)
                    elif attr_name == "max":
                        max = int(attr_value)
                    elif attr_name == "default":
                        default = int(attr_value)
                    elif attr_name == "value":
                        value = int(attr_value)
                    elif attr_name == "step":
                        step = int(attr_value)
            proplist.append(IntegerCamProp(
                min=min,
                max=max,
                default=default,
                value=value,
                step=step,
                name=name,
            ))
    return proplist