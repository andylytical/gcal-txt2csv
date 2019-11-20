#!/usr/bin/python3

import datetime
import re
import pprint


class Time:
    #                                     HOUR_______   SECOND____   AM/PM_
    re_valid_time = re.compile( '([0-9]{1,2}):?([0-9]{2})? ?([AP]M)?' )

    # default must be a str2time.Time object
    def __init__( self, time_str, default=None ):
        self.time_str = time_str
        self.default = default
        self.hour = None
        self.minute = None
        self.pm = None
        self.time = None
        self._parse_time()

    def _parse_time( self ):
        match = self.re_valid_time.search( self.time_str.upper() )
        if match:
            self.hour = int( match.group( 1 ) )
            self.minute = match.group( 2 )
            if self.minute is None:
                self.minute = 0
            else:
                self.minute = int( self.minute )
            self.pm = match.group( 3 )
            if self.pm is None:
                if self.default:
                    self.pm = self.default.pm
            if 'PM' in self.pm:
                self.hour = self.hour%12 + 12
            self.time = datetime.time( self.hour, self.minute )
        else:
            raise UserWarning( f"Invalid input for Parsed_Time '{self.time_str}'" )

    def __str__( self ):
        return f"<str2time.Time ({self.hour}:{self.minute} {self.pm})>"

    __repr__ = __str__
