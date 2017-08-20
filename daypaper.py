import requests
import datetime
import pytz
import sys
import os
import time

NUM_DAY_TRANSITIONS = 5
NUM_NIGHT_TRANSITIONS = 3
FULL_DAY_SECONDS = 24*3600
SLEEP_INTERVAL = 60*5

TIMEZONE = "US/Eastern"
IMAGE_DIRECTORY = "./dynamic_wallpaper"
VALID_EXTENTIONS = [".png", ".jpg", ".jpeg"]
FEH_COMMAND = "feh --bg-fill {}"

G_IMAGE_FILES = []
G_TRANSITION_TIMES = []
G_TRANSITION_INDEX_TABLE = []

def timeToSeconds(t):
    return (t.hour*3600 + t.minute*60 + t.second) % FULL_DAY_SECONDS

def getCurrentTimeInSeconds():
    return timeToSeconds(datetime.datetime.now().time())

def secondsToTime(s):
    s %= FULL_DAY_SECONDS
    h = 0
    m = 0
    h = s/3600
    s %= 3600
    m = s/60
    s %= 60
    return datetime.time(h,m,s)

def generateLookupTable(l):
    return dict([(j,k) for k,j in enumerate(l)])

def updateTimes(latitude, longitude):
    data = {'lat':latitude, 'lng':longitude}
    resp = requests.get('https://api.sunrise-sunset.org/json', params=data)
    res = resp.json()['results']
    sunrise = res['sunrise']
    sunset = res['sunset']

    f = "%I:%M:%S %p"
    sunrise_time = datetime.datetime.strptime(sunrise, f)
    sunset_time = datetime.datetime.strptime(sunset, f)

    tz = pytz.timezone(TIMEZONE)
    today = datetime.datetime.today()
    sunrise_time = datetime.datetime.combine(today, sunrise_time.time())
    sunrise_time = tz.normalize(sunrise_time.replace(tzinfo=pytz.utc)).time()
    sunset_time = datetime.datetime.combine(today, sunset_time.time())
    sunset_time = tz.normalize(sunset_time.replace(tzinfo=pytz.utc)).time()

    sunrise_sec = timeToSeconds(sunrise_time)
    sunset_sec = timeToSeconds(sunset_time)

    day_length = abs(sunset_sec - sunrise_sec)
    night_length = FULL_DAY_SECONDS - day_length
    day_transition_interval = day_length / NUM_DAY_TRANSITIONS
    night_transition_interval = night_length / NUM_NIGHT_TRANSITIONS

    day_transitions = []
    night_transitions = []

    for i in range(NUM_DAY_TRANSITIONS-1):
        day_transitions.append(sunrise_sec + day_transition_interval*(i+1))

    for i in range(NUM_NIGHT_TRANSITIONS-1):
        night_transitions.append(sunset_sec + night_transition_interval*(i+1))

    tr = [sunrise_sec] + day_transitions + [sunset_sec] + night_transitions
    tr = [t % FULL_DAY_SECONDS for t in tr]
    return (tr, generateLookupTable(tr))

def fileFilter(filename):
    filename = filename.lower()
    return any([filename.endswith(ext) for ext in VALID_EXTENTIONS])

def getImageFiles(dir_path):
    dir_path = os.path.abspath(dir_path)
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


prev_time = -1
current_time = -1
update = True

while True:
    if current_time != -1:
        time.sleep(SLEEP_INTERVAL)
    if update:
        G_IMAGE_FILES = getImageFiles(IMAGE_DIRECTORY)
        new_tr = updateTimes(latitude_in, longitude_in)
        (G_TRANSITION_TIMES, G_TRANSITION_INDEX_TABLE) = new_tr
        if current_time >= FULL_DAY_SECONDS:
            current_time %= FULL_DAY_SECONDS
        update = False
        print datetime.datetime.now()
        print "Found {} files".format(len(G_IMAGE_FILES))
        tr_str = [str(x) for x in G_TRANSITION_TIMES]
        print "Transition times: {}".format(', '.join(tr_str))
    prev_time = current_time
    current_time = getCurrentTimeInSeconds()
    # check if the seconds have wrapped
    if prev_time > current_time:
        # add a full day so the comparisions work out
        current_time += FULL_DAY_SECONDS
        # schedule an update
        update = True
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
