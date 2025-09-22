

def is_number(s):
    if s is not None:
        try:
            float(s)
            return True
        except ValueError:
            return False
    else:
        return False
