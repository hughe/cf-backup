# use thw clock asp as a placeholder for now.
from time import asctime, sleep, gmtime

from pitop.miniscreen import Miniscreen

m = Miniscreen()
while True:
    t = gmtime()
    m.display_text(asctime(t), font_size=8)
    sleep(1)
