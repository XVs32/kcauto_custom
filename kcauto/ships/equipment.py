
class equipment():

    itemId = 0 #type id
    masterId = 0 #production id
    stars = 0
    lock = 0
    ace = 0 
    
    def __init__(self, itemId = None, masterId = None, stars = None, lock = None, ace = None):
        self.update(itemId, masterId, stars, lock, ace)

    def update(self, itemId = None, masterId = None, stars = None, lock = None, ace = None):
        if itemId is not None:
            self.itemId = itemId

        if masterId is not None:
            self.masterId = masterId
        
        if stars is not None:
            self.stars = stars
        
        if lock is not None:
            self.lock = lock
            
        if ace is not None:
            self.ace = ace
