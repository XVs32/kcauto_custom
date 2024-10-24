from kca_enums.enum_base import EnumBase

class NodeEnum(EnumBase):

    _ignore_ = 'cnt', 'letter'

    # Generate nodes N0 to N49
    for cnt in range(0,50):
        locals()['N' + str(cnt)] = cnt

    # Generate nodes NA to NZ
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        locals()['N' + letter] = letter

    # Generate nodes NA0 to NZ49
    # Generate nodes NAA0 to NZZ49
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        for cnt in range(0,50):
            locals()['N' + letter + str(cnt)] = letter + str(cnt)
            locals()['N' + letter + letter + str(cnt)] = letter + letter + str(cnt)


    @property
    def display_name(self):
        return str(self.value)