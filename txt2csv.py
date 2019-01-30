import fileinput
import datetime
import logging
import re
import collections
import pprint
import argparse
import yaml

#logging.basicConfig( level=logging.INFO )
logging.basicConfig( level=logging.DEBUG )

Description = '''
Convert text from Google Calendar search output into CSV or HTML

Full details at: https://github.com/andylytical/gcal-txt2csv
'''

Location = collections.namedtuple( 'Location', ['name', 'address', 'regex' ] )

locations = {}
args = None
output_headers = []


def parse_cmdline():
    global args
    global output_headers
    header_list_types = {
        'tiny': [ 'Date', 'Description' ],
        'all': Event.known_headers,
    }
    parser = argparse.ArgumentParser( description=Description )
    parser.add_argument( '-l', '--locations', 
        help='YAML file with locations' )
    parser.add_argument( '-i', '--itype', choices=header_list_types.keys(),
        help=(' short names for header lists'
              ' ' + pprint.pformat( header_list_types ) + ''
              ' (default: %(default)s)'
        )
    )
    parser.add_argument( '-o', '--otype', choices=['csv', 'html'],
        help='Output format; (default: %(default)s)' )
    parser.add_argument( '-H', '--headers', action='append', 
        choices=Event.known_headers,
        help=(' Manually specify headers to use in output' 
              ' Overrides --itype'
        )
    )   
    parser.add_argument( 'datafile',
        help='txt data from google calendar search results' )

    defaults = { 'itype': 'all',
                 'otype': 'csv',
    }
    parser.set_defaults( **defaults )
    args = parser.parse_args()
    if args.headers:
        output_headers = args.headers
    else:
        output_headers = header_list_types[ args.itype ]


def load_locations():
    raw_data = None
    global locations
    with open( args.locations ) as f:
        raw_data = yaml.load( f )
    default = raw_data.pop( 'DEFAULT' )
    for k,v in raw_data.items():
        address = v['address']
        regex = k
        name = k
        if 'regex' in v:
            regex = v['regex']
        if 'name' in v:
            name = v['name']
        locations[ k ] = Location( name = name,
                                   address = address,
                                   regex = re.compile( regex ) )
        if k == default:
            locations[ 'DEFAULT' ] = locations[ k ]

def get_location_match( val ):
    # Try to find location in event description
    global locations
    for (k, location) in locations.items():
        re_loc = location.regex
        if re_loc.search( val ):
            return location
    # No match found
    raise UserWarning( "No location found for: '{}'".format( val ) )


def get_grade_level( val ):
    # Try to extract grade level from subject (val) passed in
    grade_levels = collections.OrderedDict()
    grade_levels[ '5th 6th' ] = 6
    grade_levels[ '5th' ] = 5
    grade_levels[ '6th' ] = 6
    grade_levels[ '7th' ] = 7

    rv = None
    for (k,v) in grade_levels.items():
        if k in val:
            rv = v
            break
    if rv is None:
        raise UserWarning( "Unable to find grade level in '{}'".format( val ) )
    return rv
    

class Event:
    #                                     HOUR_______   SECOND____   AM/PM_______
    re_starttime_from_subj = re.compile( '([0-9]{1,2}):?([0-9]{2})? ?([APM]{2})' )
    known_headers = [ 'Date', 
                      'Start', 
                      'End', 
                      'Description', 
                      'Location', 
                      'Grade', 
                      'Type' ]

    def __init__( self ):
        self.date = None
        self.all_day = False
        self.subj = None
        self.raw_location = None
        self.location = None
        self.starttime = None
        self.endtime = None

    def as_csv( self ):
        evdate = self.date.strftime( '%a %b %d %Y' )

        evstart = ''
        if self.all_day:
            # extract start time from subject
            match = self.re_starttime_from_subj.search( self.subj.upper() )
            if match:
                matches = pprint.pformat( match.groups() )
                #logging.debug( "MATCHES: '{}'".format( matches ) )
                hour = int( match.group( 1 ) )
                minute = match.group( 2 )
                pm = match.group( 3 )
                if minute is None:
                    minute = 0
                else:   
                    minute = int( match.group( 2 ) )
                if 'PM' in pm:
                    hour += 12
                self.starttime = datetime.time( hour, minute )
                self.endtime = datetime.time( hour + 1, minute )
            elif 'TBD' in self.subj:
                pass
            else:
                raise UserWarning( "No starttime found for all-day event '{}'".format( self.subj ) )
        if self.starttime:
            evstart = self.starttime.strftime( '%I:%M %p' )

        evend = ''
        if self.endtime:
            evend = self.endtime.strftime( '%I:%M %p' )

        evtype = ''
        if self.all_day:
            evtype = 'game'
        elif re.search( 'Practice|Open Gym', self.subj, re.I ):
            evtype = 'Practice'
        elif 'Grade' in self.subj:
            evtype = 'game'
        else:
            raise UserWarning( "Error detecting TYPE for: '{}'".format( self.subj ) )

        evloc = ''
        if self.location is None:
            if self.all_day:
                self.location = get_location_match( self.subj )
            else:
                self.location = locations[ 'DEFAULT' ]
        if evtype == 'game':
            evloc = "\"{}\n{}\"".format( self.location.name, self.location.address )

        evgrade = ''
        if self.grade is not None:
            evgrade = '{}'.format( self.grade )

        return ','.join( [ evdate, evstart, evend, self.subj, evloc, evgrade, evtype ] )

    @staticmethod
    def csv_hdrs():
        return ','.join([ 'Date', 'Start', 'End', 'Description', 'Location', 'Grade', 'Type' ])


def process_datafile( filename ):
    all_events = []

    # REFERENCE VARS
    months = [ 'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
               'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC' ]
    today = datetime.datetime.today()
    this_year = today.year
    next_year = today.year + 1

    # REGEX VARS
    # New record / day always starts with day-of-month followed by month, day-of-week
    re_valid_dom = re.compile( '^([0-9]{1,2})$' )
    re_valid_month = re.compile( '^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC), ',
                                 flags=re.IGNORECASE )

    # Second part of record is start-time - end-time OR 'All day'
    re_valid_time = re.compile( '([0-9]{2}:[0-9]{2})' )
    re_valid_all_day = re.compile( 'All day' )

    # Skip source calendar name
    # Skip repeat, alternate format of date (starts with day-of-week)
    re_valid_skip = re.compile( '^(Calendar|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)' )

    # loop vars
    cur_event = None
    cur_date_parts = {}
    cur_date = None

    # Loop through all input lines
    with fileinput.input( files=(filename,) ) as f:
        for l in f:
            line = l.strip()
            logging.info( "Input: '{}'".format( line ) )
            day_match = re_valid_dom.match( line )
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
                end = parts[-1].split( ':' )
                cur_event.starttime = datetime.time( hour=int(start[0]), minute=int(start[1]) )
                cur_event.endtime = datetime.time( hour=int(end[0]), minute=int(end[1]) )
            elif re_valid_all_day.search( line ):
                logging.debug( "ALL DAY" )
                logging.debug( "NEW EVENT" )
                cur_event = Event()
                all_events.append( cur_event )
                cur_event.date = cur_date
                cur_event.all_day = True
            elif re_valid_skip.search( line ):
                logging.debug( "SKIP" )
            else:
                # Line is either subject or location
                if cur_event.subj is None:
                    logging.debug( "SUBJECT" )
                    cur_event.subj = line
#                    if args.itype == 'sports':
#                        cur_event.grade = get_grade_level( line )
                else:
                    cur_event.raw_location = line
#                    if args.locations:
#                        cur_event.location = get_location_match( line )
#                        logging.debug( "SET LOCATION TO '{}'".format( cur_event.location.name ) )
#                    else:
#                        # no locations given, so merge second line with subject
#                        cur_event.subj += ' ' + line
    return all_events


def print_csv( event_list ):
    print( Event.csv_hdrs() )
    for e in event_list:
        print( e.as_csv() )


def run():
    parse_cmdline()
    pprint.pprint( output_headers )
    raise SystemExit()
    if args.locations:
        load_locations()
    events = process_datafile( args.datafile )
    f = getattr( __name__, 'print_'+ args.otype )
    f( events )
    #print_csv( events )


if __name__ == '__main__':
    run()
