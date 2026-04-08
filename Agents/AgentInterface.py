from abc import ABC, abstractmethod

class AgentInterface(ABC):

    @abstractmethod
    def get_move(self, board, color):
        pass

    @abstractmethod
    def get_color(self):
        pass