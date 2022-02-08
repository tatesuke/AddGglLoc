import argparse

class ThrowingArgumentParser(argparse.ArgumentParser):

    def error(self, messege):
        raise ArgumentParserException(str(messege))

class ArgumentParserException(Exception):
    pass