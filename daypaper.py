import requests
import datetime
import pytz
import sys
import os
import time

NUM_DAY_TRANSITIONS = 5
NUM_NIGHT_TRANSITIONS = 3
FULL_DAY = datetime.timedelta(days=1)
SLEEP_INTERVAL = 60*5

TIMEZONE = pytz.timezone("US/Eastern")
IMAGE_DIRECTORY = "./dynamic_wallpaper"
VALID_EXTENTIONS = [".png", ".jpg", ".jpeg"]
FEH_COMMAND = "feh --bg-fill {}"

G_IMAGE_FILES = []
G_TRANSITION_TIMES = []
G_TRANSITION_INDEX_TABLE = []

def generateLookupTable(l):
    return dict([(j,k) for k,j in enumerate(l)])

def updateTimes(latitude, longitude):
    data = {'lat':latitude, 'lng':longitude}
    resp = requests.get('https://api.sunrise-sunset.org/json', params=data)
    res = resp.json()['results']
    sunrise_str = res['sunrise']
    sunset_str = res['sunset']
    day_length_str = res['day_length']

    f = "%I:%M:%S %p"
    sunrise = datetime.datetime.strptime(sunrise_str, f).replace(tzinfo=pytz.utc)
    sunset = datetime.datetime.strptime(sunset_str, f).replace(tzinfo=pytz.utc)

    today = datetime.datetime.now().date()
    sunrise = datetime.datetime.combine(today, sunrise.timetz()).astimezone(TIMEZONE)
    sunset = datetime.datetime.combine(today, sunset.timetz()).astimezone(TIMEZONE)

    day_length = [int(x) for x in day_length_str.split(':')]
    day_length = sum([x*(60**i) for i,x in enumerate(day_length[::-1])][::-1])
    day_length = datetime.timedelta(seconds=day_length)
    night_length = FULL_DAY - day_length

    day_delta = day_length / NUM_DAY_TRANSITIONS
    night_delta = night_length / NUM_NIGHT_TRANSITIONS

    transitions = []
    for i in range(NUM_DAY_TRANSITIONS):
        transitions.append(sunrise + (day_delta*i))
    for i in range(NUM_NIGHT_TRANSITIONS):
        transitions.append(sunset + (night_delta*i))

    print "SUNRISE:",sunrise
    print "SUNSET:",sunset
    print "Transition times:"
    for i in range(len(transitions)):
        print "{}: {}".format(i, transitions[i])

    return transitions

def fileFilter(filename):
    filename = filename.lower()
    return any([filename.endswith(ext) for ext in VALID_EXTENTIONS])

def getImageFiles(dir_path):
    script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
    dir_path = script_dir + '/' + dir_path
    files = os.listdir(dir_path)
    files = filter(fileFilter, files)
    files.sort()
    files = [dir_path + "/" + p for p in files]
    return files

argc = len(sys.argv)
if argc < 3:
    print "usage: %s <latitude> <longitude>" %  sys.argv[0]
    sys.exit(0)

try:
    latitude_in = sys.argv[1]
    longitude_in = sys.argv[2]
except ValueError:
    print "latitude and longitude must be given in decimal degrees"
    sys.exit(0)

prev_time = None
current_time = None
update = True

while True:
    if update:
        update = False
        G_IMAGE_FILES = getImageFiles(IMAGE_DIRECTORY)
        G_TRANSITION_TIMES = updateTimes(latitude_in, longitude_in)
        G_TRANSITION_INDEX_TABLE = generateLookupTable(G_TRANSITION_TIMES)
        current_time = datetime.datetime.now(TIMEZONE)
        # set previous time to yesterday at 23:59:59 (before any time today)
        prev_time = datetime.datetime.combine(current_time.date(), datetime.time(0,0,0, tzinfo=TIMEZONE))
        prev_time -= datetime.timedelta(seconds=1)
        print "Updating transition times at",current_time
        print "Found {} files".format(len(G_IMAGE_FILES))
    else:
        time.sleep(SLEEP_INTERVAL)
        prev_time = current_time
        current_time = datetime.datetime.now(TIMEZONE)

    if prev_time > G_TRANSITION_TIMES[-1]:
        update = True
        continue
    transitions_hit = filter(lambda t: prev_time < t and t <= current_time, G_TRANSITION_TIMES)
    if len(transitions_hit) == 0:
        continue
    # pick the latest one if we covered multiple (or if we just launched)
    tr = transitions_hit[-1]
    index = G_TRANSITION_INDEX_TABLE[tr]
    filename = G_IMAGE_FILES[index]
    command = FEH_COMMAND.format(filename)
    print "Running command: '{}'".format(command)
    os.system(command)
