# N_Triple_Parser
This is a tool used to read through a set of N-Triples in turtle format to 
clean and modify them as needed. Depending on the size of your database, this
may take hours to run.

## Requirements
python3

## Running
The simple run case: `python3 trip_parser.py trips.trig`

This expects the trips.trig file to contain a graph block of triples. 

# Helper Functions
## clean_data
Each triple section type (IRI, Literal, etc) has a cleaning function called
clean_data. You can add whatever data cleaning logic you'd like here.

## bad_line
A helper function designed to remove bad lines from the triples before they
are processed. It uses simple string matching to see if a bad string exists
in the triple data.
