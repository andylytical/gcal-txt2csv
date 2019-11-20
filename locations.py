#!/usr/bin/python3

import collections
import yaml
import re
import pprint

Location = collections.namedtuple( 'Location', ['name', 'address', 'regex' ] )

class Locations:

    def __init__( self, infile ):
        self.locations = {}
        self.filename = infile
        self._load()

    def _load( self ):
#        raw_data = None
        with open( self.filename ) as f:
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
            self.locations[ k ] = Location(
                name = name,
                address = address,
                regex = re.compile( regex )
            )
            if k == default:
                self.locations[ 'DEFAULT' ] = self.locations[ k ]

    def match( self, val ):
        '''Try to find location in event description'''
        for (k, location) in self.locations.items():
            re_loc = location.regex
            if re_loc.search( val ):
                return location
        # No match found
        raise UserWarning( "No location found for: '{}'".format( val ) )

    @property
    def default( self ):
        return self.locations[ 'DEFAULT' ]
