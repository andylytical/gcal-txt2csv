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

import event
import str2time
import locations

#logging.basicConfig( level=logging.INFO )
logging.basicConfig( level=logging.DEBUG )

Description = '''
Convert text from Google Calendar search output into CSV or HTML

Full details at: https://github.com/andylytical/gcal-txt2csv
'''

locations_list = {}
args = None
output_headers = []


def parse_cmdline():
    global args
    global output_headers
    header_list_types = {
        'tiny': [ 'Date', 'Description' ],
        'menu': [ 'DOM', 'DOW', 'Description' ],
        'short': [ 'DOM', 'Mon_Yr_DOW', 'Start_End', 'Description', 'Location' ],
        'sports': [ 'Date', 'Start', 'End', 'Description', 'Location', 'Grade', 'Type' ],
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

    defaults = { 'headers': 'menu',
                 'otype': 'html',
    }
    parser.set_defaults( **defaults )
    args = parser.parse_args()
    output_headers = header_list_types[ args.headers ]


def process_datafile( filename ):
    global locations_list
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
    re_valid_time = re.compile( '[0-9][ap]m$' )
    #re_valid_time = re.compile( 'pm' )
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
            logging.info( f"Input: '{line}'" )
            day_match = re_valid_dom.match( line )
            month_match = re_valid_month.match( line )
            time_match = re_valid_time.search( line )
            if day_match:
                logging.debug( "NEW DAY" )
                cur_date_parts = { 'day': int( day_match.group(1) ) }
                cur_date = None
            elif month_match:
                logging.debug( "MONTH" )
                month_name = month_match.group(1).upper()
                logging.debug( f"Got month: '{month_name}'" )
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
                logging.debug( f"NEW DATE SET TO '{cur_date}'" )
            elif time_match:
                logging.debug( "START END TIMES" )
                logging.debug( "NEW EVENT" )
                cur_event = event.Event( locations_list )
                all_events.append( cur_event )
                cur_event.date = cur_date
                first, *middle, last = line.split()
                end = str2time.Time( last )
                logging.debug( "end '{}'".format( pprint.pformat( end ) ) )
                # if both time are in AM or PM, then only "end" will have the AM/PM designation
                start = str2time.Time( first, default=end )
                logging.debug( "start '{}'".format( pprint.pformat( start ) ) )
                cur_event.starttime = start.time
                cur_event.endtime = end.time
            elif re_valid_all_day.search( line ):
                logging.debug( "ALL DAY" )
                logging.debug( "NEW EVENT" )
                cur_event = event.Event( locations_list )
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
                    logging.debug( "RAW_LOCATION" )
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
    global locations_list
    parse_cmdline()
    logging.debug( "Output Headers: '{}'".format( pprint.pformat( output_headers ) ) )
    if args.locations:
        locations_list = locations.Locations( args.locations )
    events = process_datafile( args.datafile )
    f = globals()[ 'print_'+ args.otype ]( events )


if __name__ == '__main__':
    run()
