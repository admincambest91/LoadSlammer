

from abc import ABC, abstractmethod


class Test(ABC):
    @abstractmethod
    def setup(self, equipment, parameters):
        pass

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def clean_up(self):
        pass

    @abstractmethod
    def describe(self):
        pass
