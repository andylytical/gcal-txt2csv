#!/usr/bin/python3

import collections
#import csv
import datetime
#import logging
import re
#import sys
#import yaml
import pprint

#logging.basicConfig( level=logging.INFO )
#logging.basicConfig( level=logging.DEBUG )

class Event:
    #                                     HOUR_______   SECOND____   AM/PM_______
    re_starttime_from_subj = re.compile( '([0-9]{1,2}):?([0-9]{2})? ?([APM]{2})' )

    def __init__( self, locations ):
        self.locations = locations
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
            elif re.search( 'TBD|TBA|Tentative|Regional|Sectional', self.subj, re.I ):
                return 'TBD'
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
        elif re.search( 'Game|Tourn|Regional|Sectional|State| (vs\.?|@) ', self.subj, re.I ):
            evtype = 'game'
        else:
            raise UserWarning( "Error detecting TYPE for: '{}'".format( self.subj ) )
        return evtype

    def fmt_Location( self ):
        evloc = ''
        if self.raw_location is None:
            if self.all_day:
                self.location = self.locations.match( self.subj )
            else:
                self.location = self.locations.default
        else:
            self.location = self.locations.match( self.raw_location )
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
        grade_levels[ '7GVB' ] = 7
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

