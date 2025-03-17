from abc import ABC, abstractmethod

class Subject:
    """
    Subject class to allow the BIDS handler to listen for new keywords.
    """
    def add_meta_observer(self, observer):
        if observer not in self._meta_observers:
            self._meta_observers.append(observer)

    def add_data_observer(self, observer):
        if observer not in self._data_observers:
            self._data_observers.append(observer)

    def add_postprocessor_observer(self, observer):
        if observer not in self._postprocess_observers:
            self._postprocess_observers.append(observer)

    def notify_metadata_observers(self):
        for observer in self._meta_observers:
            observer.listen_metadata(self)

    def notify_data_observers(self):
        for observer in self._data_observers:
            observer.listen_data(self)

    def notify_postprocess_observers(self):
        for observer in self._postprocess_observers:
            observer.listen_postprocess(self)

class Observer(ABC):
    """
    Observer class to allow the BIDS handler to listen for new keywords.

    Args:
        ABC (object): Abstract Base Class object. Enforces the use of abstractmethod to prevent accidental access to listen_keyword without matching
        class in the observer.

    Raises:
        NotImplementedError: Error if the observing class doesn't have the right class object.
    """

    # Listener for BIDS keyword generation to create the correct pathing.
    @abstractmethod
    def listen_metadata(self):
        raise NotImplementedError("Subclass must implement abstract method")
    
    # Listener for backend data work
    @abstractmethod
    def listen_data(self):
        raise NotImplementedError("Subclass must implement abstract method")