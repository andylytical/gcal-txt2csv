import fileinput
import datetime
import logging
import re
import collections

#logging.basicConfig( level=logging.INFO )
logging.basicConfig( level=logging.DEBUG )

Location = collections.namedtuple( 'Location', ['name', 'address' ] )

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
                     address="" ),
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
    'TBD': Location( name="TBD",
                     address="" ),
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
    re.compile( 'TBD' ) : locations[ 'TBD' ],
}

months = [ 'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
           'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC' ]

today = datetime.datetime.today()
this_year = today.year
next_year = today.year + 1

#re_valid_time = re.compile( '([0-9]{2}:[0-9]) [^0-9]+ ([0-9]{2}:[0-9])' )
re_valid_time = re.compile( '([0-9]{2}:[0-9]{2})' )

re_valid_day = re.compile( '^([0-9]{1,2})$' )
re_valid_month = re.compile( '^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC), ' )

#re_valid_date = re.compile(
#    '(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* [0-9]{1,2}, [0-9]{4}' )

re_valid_subj = re.compile( 'GVB' )

re_valid_away_game = re.compile( 'All day' )

re_valid_skip = re.compile( '^(Calendar|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)' )


def get_location_match( val ):
    # Try to find location in event description
    for (re_loc, location) in re_locations.items():
        if re_loc.search( val ):
            return location
    # No match found
    raise UserWarning( "No location found for: '{}'".format( val ) )


def get_grade_level( val ):
    # Try to extract grade level from subject (val) passed in
    grade_levels = { '5th': 5, '6th': 6, '7th': 7 }
    rv = None
    for (k,v) in grade_levels.items():
        if k in val:
            rv = v
            break
    if rv is None:
        raise UserWarning( "Unable to find grade level in '{}'".format( val ) )
    return rv
    

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

        evgrade = ''
        if self.grade is not None:
            evgrade = '{}'.format( self.grade )

        return ','.join( [ evdate, evstart, evend, self.subj, evloc, evgrade, evtype ] )

    @staticmethod
    def csv_hdrs():
        return ','.join([ 'Date', 'Start', 'End', 'Description', 'Location', 'Grade', 'Type' ])


cur_event = None
all_events = []
cur_date_parts = {}
cur_date = None

for l in fileinput.input():
    #line = l.decode( 'utf8', 'ignore' )
    line = l.strip()
    logging.info( "Input: '{}'".format( line ) )
    day_match = re_valid_day.match( line )
    month_match = re_valid_month.match( line )
    time_match = re_valid_time.match( line )
    if day_match:
        logging.debug( "NEW DAY" )
        cur_date_parts = { 'day': int( day_match.group(1) ) }
        cur_date = None
    elif month_match:
        logging.debug( "MONTH" )
        month_name = month_match.group(1).upper()
        logging.debug( "Got month: '{}'".format( month_name ) )
        cur_date_parts[ 'month' ] = months.index( month_name ) + 1
        if cur_date_parts[ 'month' ] >= today.month:
            cur_date_parts[ 'year' ] = this_year
        else:
            cur_date_parts[ 'year' ] = next_year
        cur_date = datetime.date( year = cur_date_parts[ 'year' ],
                                  month = cur_date_parts[ 'month' ],
                                  day = cur_date_parts[ 'day' ] )
        logging.debug( "NEW DATE SET TO '{}'".format( cur_date ) )
    elif time_match:
        logging.debug( "START END TIMES" )
        logging.debug( "NEW EVENT" )
        cur_event = Event()
        all_events.append( cur_event )
        cur_event.date = cur_date
        parts = line.split()
        start = parts[0].split( ':' )
#       logging.debug( "  start_parts: {}".format( start ) )
        end = parts[-1].split( ':' )
#       logging.debug( "  end_parts: {}".format( end ) )
        cur_event.starttime = datetime.time( hour=int(start[0]), minute=int(start[1]) )
        cur_event.endtime = datetime.time( hour=int(end[0]), minute=int(end[1]) )
    elif re_valid_subj.search( line ):
        logging.debug( "SUBJECT" )
        cur_event.subj = line
        cur_event.grade = get_grade_level( line )
    elif re_valid_away_game.search( line ):
        logging.debug( "ALL DAY" )
        logging.debug( "NEW EVENT" )
        cur_event = Event()
        all_events.append( cur_event )
        cur_event.date = cur_date
        # AWAY GAME
        cur_event.away = True
    elif re_valid_skip.search( line ):
        logging.debug( "SKIP" )
        pass
    else:
        cur_event.location = get_location_match( line )
        logging.debug( "SET LOCATION TO '{}'".format( cur_event.location.name ) )
        #raise UserWarning( "Unmatched line: '{}'".format( line ) )

print( Event.csv_hdrs() )
for e in all_events:
    print( e.as_csv() )
