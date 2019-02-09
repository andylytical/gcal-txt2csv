#!/usr/bin/python3

import argparse
import collections
import csv
import datetime
import fileinput
import logging
import re
import sys
import yaml
import pprint

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
        'menu': [ 'DOM', 'DOW', 'Description' ],
        'sports': [ 'Date', 'Start', 'End', 'Description', 'Location', 'Grade', 'Type' ],
        'short': [ 'DOM', 'Mon_Yr_DOW', 'Start_End', 'Description', 'Location' ],
    }
    parser = argparse.ArgumentParser( description=Description )
    parser.add_argument( '-l', '--locations', 
        help='YAML file with locations' )

    htype = parser.add_mutually_exclusive_group()
    for k,v in header_list_types.items():
        optname = '--' + k
        help_txt = 'Set output columns: {} (default: %(default)s)'.format( v )
        htype.add_argument( optname,
                            dest='headers',
                            action='store_const',
                            const=k,
                            help=help_txt 
                          )

    parser.add_argument( 'datafile',
        help='txt data from google calendar search results' )

    otype = parser.add_mutually_exclusive_group()
    otype.add_argument( '--csv', dest='otype', action='store_const', const='csv',
        help='Format output as CSV (default: %(default)s)'
    )
    otype.add_argument( '--html', dest='otype', action='store_const', const='html',
        help='Format output as HTML (default: %(default)s)'
    )

    defaults = { 'headers': 'short',
                 'otype': 'html',
    }
    parser.set_defaults( **defaults )
    args = parser.parse_args()
    output_headers = header_list_types[ args.headers ]


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


    

class Event:
    #                                     HOUR_______   SECOND____   AM/PM_______
    re_starttime_from_subj = re.compile( '([0-9]{1,2}):?([0-9]{2})? ?([APM]{2})' )
#    valid_headers = [ 'Date', 
#                      'Start', 
#                      'End', 
#                      'Description', 
#                      'Location', 
#                      'Grade', 
#                      'Type',
#    ]

    def __init__( self ):
        self.date = None
        self.all_day = False
        self.subj = None
        self.raw_location = None
        self.location = None
        self.starttime = None
        self.endtime = None

    def fmt_Date( self, fmt='%a %b %d %Y' ):
        return self.date.strftime( fmt )

    def fmt_DOM( self ):
        return self.fmt_Date( fmt='%d' )

    def fmt_Mon_Yr_DOW( self ):
        return self.fmt_Date( fmt='%b %Y, %a' )

    def fmt_DOW( self ):
        return self.fmt_Date( fmt='%a' )

    def fmt_Description( self ):
        return self.subj

    def fmt_Start( self ):
        evstart = ''
        if self.all_day:
            # check subject for anything that looks like a start time
            # (useful when scheduler puts game startime in text of the event)
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
        return evstart

    def fmt_End( self ):
        evend = ''
        if self.endtime:
            evend = self.endtime.strftime( '%I:%M %p' )
        return evend

    def fmt_Start_End( self ):
        return self.fmt_Start() + ' - ' + self.fmt_End()

    def fmt_Type( self ):
        evtype = ''
        if self.all_day:
            evtype = 'game'
        elif re.search( 'Practice|Open Gym', self.subj, re.I ):
            evtype = 'Practice'
        elif 'Grade' in self.subj:
            evtype = 'game'
        else:
            raise UserWarning( "Error detecting TYPE for: '{}'".format( self.subj ) )
        return evtype

    def fmt_Location( self ):
        evloc = ''
        if self.raw_location is None:
            if self.all_day:
                self.location = get_location_match( self.subj )
            else:
                self.location = locations[ 'DEFAULT' ]
        else:
            self.location = get_location_match( self.raw_location )
        if self.fmt_Type() == 'game':
            evloc = "{}\n{}".format( self.location.name, self.location.address )
        return evloc

    def fmt_Grade( self ):
        # Try to extract grade level from subject
        grade_levels = collections.OrderedDict()
        grade_levels[ '5th 6th' ] = 6
        grade_levels[ '5th' ] = 5
        grade_levels[ '6th' ] = 6
        grade_levels[ '7th' ] = 7
        grade_levels[ '8th' ] = 8

        rv = None
        for (k,v) in grade_levels.items():
            if k in self.subj:
                rv = v
                break
        if rv is None:
            raise UserWarning( "Unable to find grade level in '{}'".format( self.subj ) )
        return rv

    def format_parts( self, headers=['Date','Description'] ):
        outparts = []
        for h in headers:
            f = getattr( self, 'fmt_' + h )
            outparts.append( f() )
        return outparts


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
    all_months = '|'.join( months )
    month_match_str = f"^({all_months})( [0-9]{{4}})?, "
    re_valid_month = re.compile( month_match_str, flags=re.IGNORECASE )

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
                # try to extract year from RE match
                year = month_match.group(2)
                if len( year ) > 0:
                    cur_date_parts[ 'year' ] = int( year )
                else:
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
                else:
                    cur_event.raw_location = line
    return all_events


def print_csv( event_list ):
    cw = csv.writer( sys.stdout )
    cw.writerow( output_headers )
    for e in event_list:
        cw.writerow( e.format_parts( output_headers ) )


def print_html( event_list ):
    #TODO: use http://www.yattag.org/
    import yattag
    # make table of events
    t_doc, t_tag, t_text, t_line = yattag.Doc().ttl()
    with t_tag( 'table', klass='calendar' ):
        for e in event_list:
            with t_tag( 'tr' ):
                ev_parts = e.format_parts( output_headers )
                for i,h in enumerate( output_headers ):
                    t_line( 'td', ev_parts[i], klass=h )

    doc, tag, text = yattag.Doc().tagtext()
    with tag( 'html' ):
        with tag( 'head' ):
            doc.stag( 'link', rel='stylesheet', type='text/css', href='gcal.css' )
        with tag( 'body' ):
            doc.asis( t_doc.getvalue() )

    print( doc.getvalue() )



def run():
    parse_cmdline()
    logging.debug( "Output Headers: '{}'".format( pprint.pformat( output_headers ) ) )
    if args.locations:
        load_locations()
    events = process_datafile( args.datafile )
    f = globals()[ 'print_'+ args.otype ]( events )


if __name__ == '__main__':
    run()
