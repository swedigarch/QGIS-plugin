class Cache:
    def __init__(self, size):
        self.size = size
        self.data = {}

    def insert(self, key, value):
        if len(self.data) >= self.size:
            self.data.pop(next(iter(self.data)))
        self.data[key] = value

    def get(self, key):
        return self.data.get(key)

    def clear(self):
        self.data.clear()