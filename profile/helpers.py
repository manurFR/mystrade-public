class UserNameCache(object):

    cache = {}

    def get_name(self, user):
        if user.id in self.cache:
            return self.cache[user.id]
        else:
            name = user.name
            self.cache[user.id] = name
            return name

