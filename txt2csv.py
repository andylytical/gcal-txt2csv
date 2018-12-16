import fileinput
import datetime
import logging
import re
import collections

#logging.basicConfig( level=logging.INFO )
logging.basicConfig( level=logging.DEBUG )

Location = collections.namedtuple( 'Location', ['name', 'address' ] )

months = ( 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec' )

locations = {
    'Blue Ridge': Location( name='Blue Ridge Junior High School',
                            address='247 S McKinley St, Mansfield, IL 61854' ),
    'Corpus Christi': Location( name='Corpus Christi Catholic School',
                                address='1909 E Lincoln St, Bloomington, IL 61701' ),
    'Deland': Location( name='De Land Weldon Elementary School',
                        address='304 IL-10, De Land, IL 61839' ),
    'Gifford': Location( name="Gifford Public School", 
                         address="406 S Main St, Gifford, IL 61847" ),
    'HCS': Location( name="Holy Cross School",
                     address="410 W White St, Champaign, IL 61820, USA" ),
    'Holy Family': Location( name="Holy Family Catholic Church",
                             address="444 E Main St, Danville, IL 61832" ),
    'Judah': Location( name="Judah",
                       address="908 N Prospect Ave, Champaign, IL 61820" ),
    'Mahomet-Seymour': Location( name="Mahomet-Seymour Junior High",
                                 address="201 W State St, Mahomet, IL 61853" ),
    'Next Gen': Location( name="Next Generation School",
                         address="2511 Galen Dr, Champaign, IL 61821" ),
    'St Joe': Location( name="St. Joseph",
                        address="606 Peters Dr, St Joseph, IL 61873" ),
    'Malachy': Location( name="St. Malachy's Catholic Church",
                         address="340 E Belle Ave, Rantoul, IL 61866" ),
    'St Matt': Location( name="St. Matthew Catholic School",
                         address="1307 Lincolnshire Dr, Champaign, IL 61821" ),
    'Tabernacle': Location( name="Tabernacle Baptist Church",
                            address="650 N Wyckles Rd, Decatur, IL 62522" ),
    'Thomasboro': Location( name="Thomasboro Grade School",
                            address="201 N Phillips St, Thomasboro, IL 61878" ),
}

re_locations = {
    re.compile( 'Blue Ridge' ) : locations[ 'Blue Ridge' ],
    re.compile( 'Corpus Christi' ) : locations[ 'Corpus Christi' ],
	re.compile( 'Deland' ) : locations[ 'Deland' ],
    re.compile( 'Gifford' ) : locations[ 'Gifford' ],
    re.compile( 'Holy Cross' ) : locations[ 'HCS' ],
    re.compile( 'Holy Family' ) : locations[ 'Holy Family' ],
    re.compile( 'Judah' ) : locations[ 'Judah' ],
    re.compile( 'Mahomet' ) : locations[ 'Mahomet-Seymour' ],
    re.compile( 'Next Gen(eration)?' ) : locations[ 'Next Gen' ],
    re.compile( 'St\.? Jo(e|seph)' ) : locations[ 'St Joe' ],
    re.compile( 'Malachy' ) : locations[ 'Malachy' ],
    re.compile( 'St\.? Matt' ) : locations[ 'St Matt' ],
    re.compile( 'Tabernacle' ) : locations[ 'Tabernacle' ],
    re.compile( 'Thomasboro' ) : locations[ 'Thomasboro' ],
}

today = datetime.datetime.today()

#re_valid_time = re.compile( '([0-9]{2}:[0-9]) [^0-9]+ ([0-9]{2}:[0-9])' )
re_valid_time = re.compile( '([0-9]{2}:[0-9]{2})' )

re_valid_date = re.compile(
    '(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* [0-9]{1,2}, [0-9]{4}' )

re_valid_subj = re.compile( 'GVB' )

re_valid_away_game = re.compile( 'All day' )

re_valid_skip = re.compile( '^Calendar|^([SMTWF][a-z]{2})$' )


def get_location_match( val ):
    # Try to find location in event description
    for (re_loc, location) in re_locations.items():
        if re_loc.search( val ):
            return location
    # No match found
    raise UserWarning( "No location found for: '{}'".format( val ) )
    

class Event:
    def __init__( self ):
        self.date = None
        self.away = False
        self.location = None

    def as_csv( self ):
        evdate = self.date.strftime( '%a %b %d %Y' )

        evstart = ''
        if not self.away:
            evstart = self.starttime.strftime('%I:%M %p' )

        evend = ''
        if not self.away:
            evend = self.endtime.strftime('%I:%M %p' )

        evtype = ''
        if self.away:
            evtype = 'game'
        elif re.search( 'Practice|Open Gym', self.subj, re.I ):
            evtype = 'Practice'
        elif 'Grade' in self.subj:
            evtype = 'game'
        else:
            raise UserWarning( "Error detecting TYPE for: '{}'".format( self.subj ) )

        evloc = ''
        if self.location is None:
            if self.away:
                self.location = get_location_match( self.subj )
            else:
                self.location = locations[ 'HCS' ]
        if evtype == 'game':
            evloc = "\"{}\n{}\"".format( self.location.name, self.location.address )

        return ','.join( [ evdate, evstart, evend, self.subj, evloc, evtype ] )

    @staticmethod
    def csv_hdrs():
        return ','.join([ 'Date', 'Start', 'End', 'Description', 'Location', 'Type' ])


cur = None
all_events = []

for l in fileinput.input():
    logging.info( "Input: '{}'".format( l ) )
    #line = l.decode( 'utf8', 'ignore' )
    line = l.strip()
    parts = line.split()
    if re_valid_date.search(line):
        logging.debug( "NEW RECORD" )
        cur = Event()
        all_events.append( cur )
        # DATE
        date_formats = [ '%A, %B %d, %Y',
                        '%b %d, %Y',
        ]
        last_err = None
        evdate = None
        for DF in date_formats:
            try:
                evdate = datetime.datetime.strptime( line, DF )
            except ( ValueError ) as e:
                last_err = e
        if evdate == None:
            raise last_err
        logging.debug( "Got Date: '{}'".format( evdate ) )
        cur.date = evdate
    elif re_valid_time.match( line ):
        logging.debug( "START END TIMES" )
        start = parts[0].split( ':' )
#       logging.debug( "  start_parts: {}".format( start ) )
        end = parts[-1].split( ':' )
#       logging.debug( "  end_parts: {}".format( end ) )
        cur.starttime = datetime.time( hour=int(start[0]), minute=int(start[1]) )
        cur.endtime = datetime.time( hour=int(end[0]), minute=int(end[1]) )
    elif re_valid_subj.search( line ):
        logging.debug( "SUBJECT" )
        cur.subj = line.strip()
    elif re_valid_away_game.search( line ):
        logging.debug( "ALL DAY" )
        # AWAY GAME
        cur.away = True
    elif re_valid_skip.search( line ):
        logging.debug( "SKIP" )
        pass
    else:
        cur.location = get_location_match( line )
        #raise UserWarning( "Unmatched line: '{}'".format( line ) )

print( Event.csv_hdrs() )
for e in all_events:
    print( e.as_csv() )
