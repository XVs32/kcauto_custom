from util.pyvisauto import Region, FindFailed
from random import randint, choice

import nav.nodes as nodes
import util.kca as kca_u
from util.logger import Log


class Navigate(object):
    """The Nav module which enables navigation and navigation side-stepping.
    All methods are class and static methods; Nav should not be directly
    instantiated.
    """
    @classmethod
    def to(cls, destination, max_sidestep=1):
        """Method to call to detect the current location and move to the
        specified destination, with or without sidesteps.

        Args:
            regions (dict): dict of pre-defined kcauto regions
            destination (str): name of the destination
            max_sidestep (int, optional): the max number of sidesteps to take;
                in the current implementation the name and type is a misnomer:
                if it is a non-zero number the code will sidestep once,
                otherwise never sidestep (should be renamed to 'sidestep' with
                bool type)

        Returns:
            bool: True if navigation was successful, False if no actions were
                taken
        """

        retry = True
        while True:

            if (kca_u.kca.exists('home_menu', 'nav|home_menu_sortie.png')
                    and destination == 'home'):
                # if visibly at home menu and destination is home, not refresh
                # home, short circuit
                return False

            sidestep = bool(randint(0, max_sidestep))
            kca_u.kca.hover('top')
            kca_u.kca.sleep()
            # Figure out where we are
            current_location = None
            if kca_u.kca.exists('home_menu', 'nav|home_menu_sortie.png'):
                Log.log_msg("At home")
                current_location = nodes.nav_nodes.home
            elif kca_u.kca.exists('side_menu', 'nav|side_menu_home.png'):
                Log.log_msg("At side menu")
                current_location = nodes.nav_nodes.side_menu
            elif kca_u.kca.exists('lower_left', 'nav|top_menu_home.png'):
                Log.log_msg("At top menu")
                current_location = nodes.nav_nodes.top_menu

            if not current_location:
                Log.log_error("Nav module could not figure out current location.")
                raise FindFailed()

            kca_u.kca.hover('top')
            kca_u.kca.sleep()
            
            if current_location.name == 'home':
                # Starting from home screen
                if destination == 'home':
                    # Already at home
                    # Util.log_msg('Already at home.')
                    return False
                elif destination == 'refresh_home':
                    # Refresh home
                    Log.log_msg("Refreshing home.")
                    destination = 'home'
                    current_location = current_location.navigate_to(
                        cls._choose_sidestep(destination), False)
                else:
                    # Go to and side menu sub screen
                    Log.log_msg(
                        "Navigating to {} screen.".format(destination))
                    if destination in ('combat', 'pvp', 'expedition'):
                        current_location = current_location.navigate_to(
                            'sortie', False)
                        kca_u.kca.sleep(1)
                    else:
                        if sidestep:
                            current_location = current_location.navigate_to(
                                cls._choose_sidestep(destination), False)
            elif current_location.name == 'side_menu':
                # Starting from a main menu item screen
                if destination in ('home', 'refresh_home'):
                    # Go or refresh home
                    Log.log_msg('Going home.')
                    destination = 'home'
            elif current_location.name == 'top_menu':
                # Starting from top menu item. Theoretically, the script should
                # never attempt to go anywhere but home from here
                if destination in ('home', 'refresh_home'):
                    Log.log_msg('Going home.')
                    destination = 'home'

            if current_location.navigate_to(destination) == False and retry == True:
                Log.log_msg('Nav to home and retry.')
                current_location = current_location.navigate_to(
                    'home', True)
                retry = False
                continue
            else:
                retry = False

            if retry == False:
                break

        return True

    @staticmethod
    def _choose_sidestep(exclude):
        """Method to choose the sidestep destination, excluding the defined
        exclusion choices (typical the destination itself).

        Args:
            exclude (list): list of all destinations that should be excluded
                from the list of available sidestep destinations

        Returns:
            str: sidestep destination
        """
        choices = [
            'fleetcomp', 'resupply', 'equipment', 'repair', 'development']
        if exclude in choices:
            choices.remove(exclude)
        sidestep_destination = choice(choices)
        return sidestep_destination


class NavigateList(object):
    """The NavList module which enables page navigation for the shiplists in
    the fleet comp and repair screens. All methods are class and static
    methods; NavList should not be directly instantiated.
    """
    # offset of navigation controls, based off of the ship comp UI's ship list,
    # in x, y pixel format
    
    OP_MODE_SHIPCOMP = 0
    OP_MODE_REPAIR = 1
    OP_MODE_EQUIPMENT = 2
    OP_MODE_EQUIPMENT_SHIP = 3
    OP_MODE_QUEST = 4

    OFFSET = {
        OP_MODE_REPAIR: (0, 0),
        OP_MODE_SHIPCOMP: (17, -4),
        OP_MODE_EQUIPMENT: (-3, -4)
    }
    
    REGION = {
        OP_MODE_REPAIR: {"first": (735 - (50*2) + OFFSET[OP_MODE_REPAIR][0], 675 + OFFSET[OP_MODE_REPAIR][1]),
                             "prev": (735 - (50*1) + OFFSET[OP_MODE_REPAIR][0], 675 + OFFSET[OP_MODE_REPAIR][1]),
                             "next": (735 + (215) + (50*1) + OFFSET[OP_MODE_REPAIR][0], 675 + OFFSET[OP_MODE_REPAIR][1]),
                             "last": (735 + (215) + (50*2) + OFFSET[OP_MODE_REPAIR][0], 675 + OFFSET[OP_MODE_REPAIR][1]),
                             1: (739 + (0 * 53) + OFFSET[OP_MODE_REPAIR][0], 675 + OFFSET[OP_MODE_REPAIR][1]),
                             2: (739 + (1 * 53) + OFFSET[OP_MODE_REPAIR][0], 675 + OFFSET[OP_MODE_REPAIR][1]),
                             3: (739 + (2 * 53) + OFFSET[OP_MODE_REPAIR][0], 675 + OFFSET[OP_MODE_REPAIR][1]),
                             4: (739 + (3 * 53) + OFFSET[OP_MODE_REPAIR][0], 675 + OFFSET[OP_MODE_REPAIR][1]),
                             5: (739 + (4 * 53) + OFFSET[OP_MODE_REPAIR][0], 675 + OFFSET[OP_MODE_REPAIR][1])},
        OP_MODE_SHIPCOMP: {"first": (735 - (50*2) + OFFSET[OP_MODE_SHIPCOMP][0], 675 + OFFSET[OP_MODE_SHIPCOMP][1]),
                                "prev": (735 - (50*1) + OFFSET[OP_MODE_SHIPCOMP][0], 675 + OFFSET[OP_MODE_SHIPCOMP][1]),
                                "next": (735 + (215) + (50*1) + OFFSET[OP_MODE_SHIPCOMP][0], 675 + OFFSET[OP_MODE_SHIPCOMP][1]),
                                "last": (735 + (215) + (50*2) + OFFSET[OP_MODE_SHIPCOMP][0], 675 + OFFSET[OP_MODE_SHIPCOMP][1]),
                                1: (739 + (0 * 53) + OFFSET[OP_MODE_SHIPCOMP][0], 675 + OFFSET[OP_MODE_SHIPCOMP][1]),
                                2: (739 + (1 * 53) + OFFSET[OP_MODE_SHIPCOMP][0], 675 + OFFSET[OP_MODE_SHIPCOMP][1]),
                                3: (739 + (2 * 53) + OFFSET[OP_MODE_SHIPCOMP][0], 675 + OFFSET[OP_MODE_SHIPCOMP][1]),
                                4: (739 + (3 * 53) + OFFSET[OP_MODE_SHIPCOMP][0], 675 + OFFSET[OP_MODE_SHIPCOMP][1]),
                                5: (739 + (4 * 53) + OFFSET[OP_MODE_SHIPCOMP][0], 675 + OFFSET[OP_MODE_SHIPCOMP][1])},
        OP_MODE_EQUIPMENT: {"first": (735 - (50*2) + OFFSET[OP_MODE_EQUIPMENT][0], 675 + OFFSET[OP_MODE_EQUIPMENT][1]),
                                "prev": (735 - (50*1) + OFFSET[OP_MODE_EQUIPMENT][0], 675 + OFFSET[OP_MODE_EQUIPMENT][1]),
                                "next": (735 + (215) + (50*1) + OFFSET[OP_MODE_EQUIPMENT][0], 675 + OFFSET[OP_MODE_EQUIPMENT][1]),
                                "last": (735 + (215) + (50*2) + OFFSET[OP_MODE_EQUIPMENT][0], 675 + OFFSET[OP_MODE_EQUIPMENT][1]),
                                1: (739 + (0 * 53) + OFFSET[OP_MODE_EQUIPMENT][0], 675 + OFFSET[OP_MODE_EQUIPMENT][1]),
                                2: (739 + (1 * 53) + OFFSET[OP_MODE_EQUIPMENT][0], 675 + OFFSET[OP_MODE_EQUIPMENT][1]),
                                3: (739 + (2 * 53) + OFFSET[OP_MODE_EQUIPMENT][0], 675 + OFFSET[OP_MODE_EQUIPMENT][1]),
                                4: (739 + (3 * 53) + OFFSET[OP_MODE_EQUIPMENT][0], 675 + OFFSET[OP_MODE_EQUIPMENT][1]),
                                5: (739 + (4 * 53) + OFFSET[OP_MODE_EQUIPMENT][0], 675 + OFFSET[OP_MODE_EQUIPMENT][1])},
        OP_MODE_QUEST: {"first": (385, 687),
                             "prev": (435 , 687),
                             "next": (920, 687),
                             "last": (970, 687),
                             1: (524, 687),
                             2: (606, 687),
                             3: (688, 687),
                             4: (770, 687),
                             5: (852, 687)},
        OP_MODE_EQUIPMENT_SHIP: {
                             "prev": (208, 664),
                             "next": (413, 664),
                             1: (243, 664),
                             2: (303, 664),
                             3: (363, 664)}}
        
    @classmethod
    def to_page(
            cls, page_count, current_page, target_page,
            op_mode= OP_MODE_SHIPCOMP):
        """Method that navigates the shiplist to the specified target page from
        the specified current page. Uses _change_page for navigation.

        Args:
            regions (dict): dict of regions
            page_count (int): total number of pages
            current_page (int): current page
            target_page (int): page to navigate to
            offset_mode (str): 'shipcomp' or 'repair', depending on what
                offsets to use for the navigation control's location; should
                match keys in OFFSET class dictionary

        Returns:
            int: new current page post-navigation
        """
        # logic that fires off the series of _change_page method calls to
        # navigate to the desired target page from the current page
        
        if op_mode == cls.OP_MODE_EQUIPMENT_SHIP:
            # no "first", "last" button in equipment ship list, 3 digits at once only, use 1, 2, 3 in _change_page
            while target_page != current_page:
                page_delta = target_page - current_page
                if target_page <= 3 and (current_page == 1 or page_count <= 3):
                    cls._change_page(target_page, op_mode)
                    current_page = target_page
                elif (current_page == page_count
                        and target_page >= page_count - 2):
                    cls._change_page(
                        abs(page_count - target_page - 3), op_mode)
                    current_page = target_page
                elif -2 < page_delta < 2:
                    cls._change_page( 2 + page_delta, op_mode)
                    current_page = current_page + page_delta
                elif page_delta <= - 2:
                    cls._change_page('prev', op_mode)
                    current_page -= 3
                    current_page = max(1, current_page)
                elif page_delta >= 2:
                    cls._change_page('next', op_mode)
                    current_page += 3
                    current_page = min(page_count, current_page)
                    
        else:
            while target_page != current_page:
                page_delta = target_page - current_page
                if target_page == 1:
                    # shortcut for first page
                    #Log.log_error("first")
                    cls._change_page('first', op_mode)
                    current_page = 1
                elif target_page == page_count:
                    # shortcut for last page
                    #Log.log_error("last")
                    cls._change_page('last', op_mode)
                    current_page = page_count
                elif target_page <= 5 and (current_page <= 3 or page_count <= 5):
                    #Log.log_error("direct 1")
                    cls._change_page(target_page, op_mode)
                    current_page = target_page
                elif (current_page >= page_count - 2
                        and target_page >= page_count - 4):
                    #Log.log_error("direct 2")
                    cls._change_page(
                        abs(page_count - target_page - 5), op_mode)
                    current_page = target_page
                elif -3 < page_delta < 3:
                    #Log.log_error("direct 3")
                    cls._change_page( 3 + page_delta, op_mode)
                    current_page = current_page + page_delta
                elif page_delta <= - 3:
                    if target_page <= 5:
                        #Log.log_error("back to first")
                        cls._change_page('first', op_mode)
                        current_page = 1
                    else:
                        #Log.log_error("prev")
                        cls._change_page('prev', op_mode)
                        if op_mode == cls.OP_MODE_QUEST:
                            current_page -= 1
                        else:
                            current_page -= 5
                elif page_delta >= 3:
                    if target_page > (page_count - 5):
                        #Log.log_error("go to last")
                        cls._change_page('last', op_mode)
                        current_page = page_count
                    else:
                        #Log.log_error("next")
                        cls._change_page('next', op_mode)
                        if op_mode == cls.OP_MODE_QUEST:
                            current_page += 1
                        else:
                            current_page += 5
        kca_u.kca.sleep(0.5)
        return current_page

    @classmethod
    def _change_page(cls, target, mode):
        """Method that clicks on the arrow and page number navigation at the
        bottom of the ship list. 'first', 'prev', 'next', 'last' targets will
        click their respective arrow buttons, while an int target between 1 and
        5 (inclusive) will click the page number at that position at the bottom
        of the page (left to right).

        Args:
            regions (dict): dict of regions
            target (str, int): specifies which navigation button to press
            offset (tuple): tuple of x, y pixel offsets as defined by
                offset_mode and the OFFSET class dictionary
        """
        Log.log_debug(f"Changing to page {target} with {mode} offsets.")
        x_start = kca_u.kca.game_x + cls.REGION[mode][target][0]
        y_start = kca_u.kca.game_y + cls.REGION[mode][target][1]
            
        if type(target) is str and target.isdigit():
            Region(x_start, y_start, 16, 15).click()
        else:
            Region(x_start, y_start, 10, 15).click()
            

        kca_u.kca.sleep(0.5)


navigate = Navigate()
navigate_list = NavigateList()
