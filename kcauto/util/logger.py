from abc import ABC
from time import strftime
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os
import sys
import io

import args.args_core as arg


class Log(ABC):
    CLR_MSG = '\033[94m'
    CLR_SUCCESS = '\033[92m'
    CLR_WARNING = '\033[93m'
    CLR_ERROR = '\033[91m'
    CLR_END = '\033[0m'

    log_file = None

    @classmethod
    def init(cls):

        # Force stdout to use UTF-8
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

        # Specify the directory path
        directory = 'log'

        # Calculate the date one month ago from the current date
        one_month_ago = datetime.now() - relativedelta(months=1)

        # Iterate over the file names in the directory
        for filename in os.listdir(directory):
            if os.path.isfile(os.path.join(directory, filename)):

                # Extract the date and time part from the filename
                date_time_str = filename[:-4]  # Remove the '.log' extension

                # Define the format of the date and time in the filename
                date_time_format = "%d-%m-%Y-%H-%M-%S"

                # Parse the date and time string into a datetime object
                date_time_obj = datetime.strptime(date_time_str, date_time_format)

                # Check if date_time_obj is one month or older
                if date_time_obj <= one_month_ago :
                    os.remove(os.path.join(directory, filename))

        # dd/mm/YY H:M:S
        dt_string = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
        cls.log_file = open( "log/" + dt_string + ".log", "w", encoding='utf-8')

    @staticmethod
    def _log_format(msg):
        """Method to add a timestamp to a log message.

        Args:
            msg (str): log message.

        Returns:
            str: log message with timestamp appended.
        """
        return f"[{strftime('%Y-%m-%d %H:%M:%S')}] {msg}"

    @classmethod
    def log_msg(cls, msg):
        """Method to print a log message to the console, with the 'msg' colors.

        Args:
            msg (str): log message.
        """
        print(
            f"{cls.CLR_MSG}{cls._log_format(msg)}{cls.CLR_END}",
            flush=True)
        cls.log_file.write(cls._log_format(msg) + "\n")
        cls.log_file.flush()
        

    @classmethod
    def log_success(cls, msg):
        """Method to print a log message to the console, with the 'success'
        colors.

        Args:
            msg (str): log message.
        """
        print(
            f"{cls.CLR_SUCCESS}{cls._log_format(msg)}{cls.CLR_END}",
            flush=True)
        cls.log_file.write(cls._log_format(msg) + "\n")
        cls.log_file.flush()

    @classmethod
    def log_warn(cls, msg):
        """Method to print a log message to the console, with the 'warning'
        colors.

        Args:
            msg (str): log message.
        """
        print(
            f"{cls.CLR_WARNING}{cls._log_format(msg)}{cls.CLR_END}",
            flush=True)
        cls.log_file.write(cls._log_format(msg) + "\n")
        cls.log_file.flush()

    @classmethod
    def log_error(cls, msg):
        """Method to print a log message to the console, with the 'error'
        colors.

        Args:
            msg (str): log message.
        """
        
        print(
            f"{cls.CLR_ERROR}{cls._log_format(msg)}{cls.CLR_END}",
            flush=True)
        cls.log_file.write(cls._log_format(msg) + "\n")
        cls.log_file.flush()

    @classmethod
    def log_debug(cls, msg):
        """Method to print a debug log message to the console. Only prints if
        the debug flag is set to True.

        Args:
            msg (str): log message.
        """
        if arg.args.parsed_args.debug_output:
            print(cls._log_format(msg), flush=True)

        cls.log_file.write(cls._log_format(msg) + "\n")
        cls.log_file.flush()
