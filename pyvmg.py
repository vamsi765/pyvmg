import re
import glob
import csv
import datetime
import os
import sys
import argparse
from operator import itemgetter
from xml.dom import minidom

def escapexml(xmldata):
    xmldata = xmldata.replace('&', '&amp;')
    xmldata = xmldata.replace('<', '&lt;')
    xmldata = xmldata.replace('>', '&gt;')
    xmldata = xmldata.replace('"', '&quot;')
    xmldata = xmldata.replace('¤', '&curren;')
    xmldata = xmldata.replace('\xe4', '&auml;')
    return xmldata

class VMGReader(object):
    """Reader for a .vmg file to get back the contact information, date, body
    """

    TEL_RE = re.compile(r'TEL:(\w+|\+?\d+)')
    DATE_RE = re.compile(r'X-NOK-DT:([\dTZ]+)')
    BODY_RE = re.compile(r'Date:[\d.: ]+\n(.*)END:VBODY',re.DOTALL)

    def read(self, filename):
        """Open a .vmg file and remove the NULL characters and store the text
            message
        """
        self.filename = filename
        self.message = open(filename, 'r', encoding='utf-8',
                            errors='surrogateescape').read()
        self.message = self.message.replace('\x00', '')

    def process(self):
        """Parse the message and return back a dictionary with
        Contact information, date and body of message
        """
        data = {}
        telmatch = self.TEL_RE.search(self.message)
        if telmatch:
            data['contact'] = telmatch.group(1)
        else:
            data['contact'] = ''
        datematch = self.DATE_RE.search(self.message)
        if datematch:
            data['date'] = datematch.group(1)
            try:
                data['date']  = datetime.datetime.strptime(data['date'],
                                                            '%Y%m%dT%H%M%SZ')
            except ValueError:
                # Use Epoch as date if no date was available
                data['date'] = datetime.datetime(1970, 1, 1, 0, 0)
        else:
            data['date'] = datetime.datetime(1970, 1, 1, 0, 0)
        bodymatch = self.BODY_RE.search(self.message)
        if bodymatch:
            data['body'] = bodymatch.group(1)
        else:
            data['body'] = ''
        return data

class Writer(object):
    """Base class for a writer object to convert all VMG files to a single file
    """

    DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

    def __init__(self, filename):
        """Create a file writer object with the filename specified
        """
        self.filename = filename
        self.file = open(filename, 'w', encoding='utf-8',
                            errors='surrogateescape')

    def __del__(self):
        self.file.close()

    def processdir(self, dirpath):
        """Given a directory path, process all the .vmg files in it and store
            as a list
        """
        files = glob.glob(dirpath + '/*.vmg')
        reader = VMGReader()
        self.messages = []
        for f in files:
            print("Processing file:", f)
            reader.read(f)
            msg = reader.process()
            msg['date'] = msg['date'].strftime(self.DATETIME_FORMAT)
            msg['file'] = f
            if any(v == '' for v in msg.values()):
                print ("missing information in ", msg)
                continue
            self.messages.append(msg)
        # Sort the messages according to date
        self.messages.sort(key=itemgetter('date'))

class XMLWriter(Writer):
    """Writer object for XML file as output
    """
    def write(self):
        """Read every message in the list and write to a XML file
        """
        xmlstr = '<messages>'
        tmpl = '''
  <message>
    <file>
      %s
    </file>
    <contact>%s</contact>
    <date>%s</date>
    <body>
      %s
    </body>
  </message>'''
        for msg in self.messages:
            xmlstr += tmpl %(msg['file'], msg['contact'], msg['date'],
                                escapexml(msg['body'])[:-1])
        xmlstr += '</messages>'
        #self.file.write(minidom.parseString(xmlstr).toprettyxml(indent="   "))
        self.file.write(xmlstr)

class CSVWriter(Writer):
    """Writer object for CSV file as output
    """
    def write(self):
        """Read every message in the list and write to a CSV file
        """
        fn = csv.writer(self.file).writerow
        fn(('contact', 'date', 'body'))
        for msg in self.messages:
            fn((msg['contact'], msg['date'], msg['body']))

class TextWriter(Writer):
    """Writer object for text file as output

    Format is
    +919900123456 - 2008-05-26 12:42:32
    Message contents goes here

    +919900123456 - 2008-05-26 12:50:32
    Second message contents goes here

    Ignores empty messages
    """
    def write(self):
        """Read every message in the list and write to a CSV file
        """
        tmpl = '''=============================
File        : %s
Contact     : %s
Date        : %s
Message     :
%s
=============================
'''
        for msg in self.messages:
            txtstr = tmpl %(msg['file'], msg['contact'], msg['date'],
                            msg['body'])
            self.file.write(txtstr)

def dir_path(string):
    if os.path.isdir(string):
        return string
    else:
        raise NotADirectoryError(string)

def read_cmd_args():
  parser = argparse.ArgumentParser()

  # Add long and short argument
  parser.add_argument("--in_dir", help="directory name",
		        nargs='+', type=dir_path,
			default=None, required=True)
  parser.add_argument("--out_filename",
                        help="output file name",
		        nargs=None,
			default="vmg.txt", required=False)

  # Read arguments from the command line
  args = parser.parse_args()
  return args

def main():
    args = read_cmd_args()

    name, ext = os.path.splitext(args.out_filename)

    if ext == ".txt":
        writer = TextWriter(args.out_filename)
    elif ext == ".csv":
        writer = CSVWriter(args.out_filename)
    elif ext == ".xml":
        writer = XMLWriter(args.out_filename)
    else:
        raise Exception("Please provide supported extension")

    for single_dir in args.in_dir:
        print("Processing directory:", single_dir)
        writer.processdir(single_dir)
        writer.write()

if __name__ == "__main__":
    main()

