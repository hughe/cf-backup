import enum
import logging
import sys

from pt_miniscreen.core import App
from pt_miniscreen.core import Component
from pt_miniscreen.core.components import Text

from pitop.miniscreen import Miniscreen

import find_disks

log = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)

class State(enum.Enum):
  SEARCHING = 1
  BACKUP_READY = 2
  BACKUP_RUNNING = 3
  BACKUP_DONE = 4
  BACKUP_ERROR = 5

SEARCHING_TEXT = "Searching\n\n\n\nX to exit"

class BackupUI(Component):
  # define a `default_state` dictionary to create state with known values
  default_state = dict(
    st=State.SEARCHING,
    src=None,
    dst=None,
    progress=0,
  )

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.text = self.create_child(
      Text,
      text=SEARCHING_TEXT,
      font_size=10,
      align="left",
      vertical_align="top",
      wrap=False,
    )
    self._tick_interval = self.create_interval(self.tick, timeout=1)
    logging.getLogger().setLevel(logging.DEBUG)  # Hit it with a stick.

  def select_button_pressed(self):
    if self.state["st"] == State.BACKUP_READY:
      self.select_in_backup_ready()

  def select_in_backup_ready(self):
    self.state.update(st=State.BACKUP_RUNNING, progress=0)
    self.update_text()

  def tick(self):
    log.warning("tick")
    if self.state["st"] == State.SEARCHING:
      self.tick_in_searching()
      

  def tick_in_searching(self):
    res = find_disks.find_disks()
    log.debug("find_disks: %s", res)
    if res.backup_a is not None and res.cf_card is not None:
      self.state.update(st=State.BACKUP_READY,
                        src=res.cf_card,
                        dst=res.backup_a)
      self.update_text()
      

  def update_text(self):
    def u(s):
      self.text.state.update(text=s)
      
    if self.state["st"] == State.SEARCHING:
      u(SEARCHING_TEXT)
    elif self.state["st"] == State.BACKUP_READY:
      u(f"Ready\nS: {self.state['src']}\nD: {self.state['dst']}\n\nO to start, X to exit")
    elif self.state["st"] == State.BACKUP_RUNNING:
      u(f"Running\nS: {self.state['src']}\nD: {self.state['dst']}\nP: {self.state['progress']}%\nX to exit")
  
  def render(self, image):
      return self.text.render(image)
    
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

