from pt_miniscreen.core import App
from pt_miniscreen.core import Component

class BackupUI(Component):
  # define a `default_state` dictionary to create state with known values
  default_state = {
  }

  def __init__(self, **kwargs):
    super().__init__(**kwargs)

  def select_button_pressed(self):
      pass
  
  def render(self, image):
      pass
    
class BackupApp(App):
  def __init__(self, miniscreen):
    super().__init__(display=miniscreen.device.display, Root=BackupUI)

    # We call methods on self, because self.root does not exist until
    # start() is run. So if we said `self.root.button_pressed` we'd
    # get an exception.
    miniscreen.select_button.when_pressed = self.select_button_pressed
    miniscreen.cancel_button.when_pressed = self.cancel_button_pressed

  def select_button_pressed(self):
    self.root.select_button_pressed()

  def cancel_button_pressed(self):
    self.stop()

def main():
  m = Miniscreen()

  a = BackupApp(m)
  
  a.start()
  a.wait_for_stop()

if __name__ == '__main__':
  main()

