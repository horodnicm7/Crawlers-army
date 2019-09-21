class Product(object):
    def __init__(self, new_price=0, old_price=0, discount=0, name='', url=''):
        self.price = new_price
        self.discount = discount
        self.name = name
        self.old_price = old_price
        self.url = url

    def display(self):
        print(self.name)
        print('Old price: {}\tNew price: {}\nDiscount: {}%'.format(self.old_price, self.price, self.discount))
        print('Url: {}\n'.format(self.url))
