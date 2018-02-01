import sys
import re
import logging

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

class TripleSectionType():
    regex_match = ".*"

    def __init__(self):
        self.data = None

    def __str__(self):
        return str(self.data)

    def load(self, line):
        remaining_line = self.get_data(line.strip())
        self.clean_data()
        return remaining_line or ""

    def get_data(self,line):
        match = re.match(self.regex_match, line)
        if match:
            self.data, remaining_line = match.group(), line[match.end():]
        else:
            raise ValueError("No %s exists in this line: %s " % (self.__class__.__name__, line))
        return remaining_line

    def clean_data(self):
        raise NotImplementedError("This function has not been implemented yet")

class Iri(TripleSectionType):
    regex_match = '(^<.*?>)'

    def clean_data(self):
        bad_chars = r'[\x00-\x20<>"{}|^`\\]'
        old_line = self.data
        self.data = re.sub(bad_chars,'',self.data)
        logger.info("IRI %s cleaned. Now: %s" % (old_line, self.data))

def get_type(line, available_types):
    #This function takes a line and available types and tries to build an
    #object from them, returning the object and whatever is left of the line.
    #This assumes each available type has the same init reqs
    rdf_obj = None
    for rdftype in available_types:
        rdf_obj = rdftype()
        try:
            line = rdf_obj.load(line)
            break
        except ValueError as valerr:
            logger.debug(valerr)
            rdf_obj = None

    if not rdf_obj: raise TypeError("Line doesn't match known types")
    return line, rdf_obj

class BlankNode(TripleSectionType):
    regex_match = '^_:[^ ]*' #TODO Need to break on whitespace

    def clean_data(self):
        pass

class Literal(TripleSectionType):
    #can be ", ', """, '''
    regex_match = """(^('{3}|'|"{3}|").*('{3}|'|"{3}|"))((\^\^)?(<.*?>))?(@[A-Za-z0-9-]*)?|[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?|(true|false)"""
    def clean_data(self):
        pass

class TripleSection():
    allowed_types = [Iri]
    def __init__(self):
        self.type = None
        self.name = None
        self.data = None
        self.is_complete = False

    def __str__(self):
        return str(self.data)

    def load(self, line):
        if self.is_complete: return line
        line, self.data = get_type(line, self.allowed_types)
        if self.data:
            logger.debug("Triple Section type: %s" % self.data.__class__.__name__)
            self.is_complete = True
        return line or ""

    def clean(self):
        self.data.clean_data()

class Subject(TripleSection):
    #Subject can be an IRI or a blank node
    allowed_types = [Iri, BlankNode]

class Predicate(TripleSection):
    #Predicates can be only IRI or 'a'
    allowed_types = [Iri]

class RDFObject(TripleSection):
    #RDFObject can be IRI, Blank, or Literal. Also, can be seperated with commas
    allowed_types = [Iri, BlankNode, Literal]

class Triple():
    states = ("subject", "predicate", "rdfobject", "close", "completed")
    __completed = states.index("completed")
    __predicate = states.index("predicate")
    __rdfobject = states.index("rdfobject")
    __close = states.index("close")
    __subject = states.index("subject")
    state_transition = {
        "subject": "predicate",
        "predicate": "rdfobject",
        "rdfobject": "close",
        "close": None,
        "completed": None,
    }

    def __init__(self):
        self.processing = ""
        self.current_input = None
        self.is_complete = False
        self.has_data = False
        self.state = self.states[0]
        self.subject = Subject()
        self.relationships = [(Predicate(),RDFObject())]

    def to_string(self, tab=False):
    #This function will be printing the string represenations of each of the relationships and the subject
        string = ''
        if tab: string += '\t'
        string += str(self.subject)
        string += '\n'

        for index, relationship in enumerate(self.relationships):
            if index != 0:
                string += ';\n'
            if tab: string += '\t'
            string += '\t'
            string += str(relationship[0]) + '\t'
            string += str(relationship[1]) + '\t'
        string += ".\n"
        return string

    def load(self,line):
        while line and not self.is_complete:
            logger.debug("triple state: %s" % self.state)

            if line.isspace(): return
            line = self.state_job[self.state](self,line)
            logger.debug("triple after load: %s" % line)

        logger.debug("triple complete: %s" % self.is_complete)
        logger.debug("returning: %s" % line)

        return line

    def build_subject(self, line):
        line = self.subject.load(line)

        if self.subject.is_complete:
            self.transition()
            logging.debug("subject complete")
            return line or ""
        return line or ""

    def get_subject():
        if data:
            return data[0]
        else:
            return Subject()

        """
        I will always, if well formed, get a predicate/object pair before a symbol.
        Symbol determines if next or end.
        Build predicate
        build object
        figure out next step:
            build a new pair, append to list
            complete triple
        """

    def build_relationship(self, line):
        relation_obj = None
        logger.debug("Triple state: %s" % self.state)
        if self.state == self.states[self.__predicate]:
            relation_obj = self.relationships[-1][0]
        elif self.state == self.states[self.__rdfobject]:
            relation_obj = self.relationships[-1][1]
        else: return line

        line = relation_obj.load(line)
        if relation_obj.is_complete:
            self.transition()

        return line

    def close_pair_or_trip(self,line):
        """

        this line should really only be a single character, after stripping it. If not, there was a problem
        if it ends in a ., the triple is done, close it.
        if it ends in a ;, the pair is done, create a new pair and append
        """
        trip_ender = '.'
        pair_ender = ';'
        end_char = line.strip()
        if end_char == pair_ender:
            new_pair = (Predicate(), RDFObject())
            self.relationships.append(new_pair)
            self.transition(jump_to=self.states[self.__predicate])
        elif end_char == trip_ender:
            self.is_complete = True
            self.transition(jump_to=self.states[self.__completed])
            logger.debug("------------------------TRIPLE COMPLETED---------------------")
        else:
            raise ValueError("This line should just be a single character. Something was parsed incorrectly. Value: %s" % end_char)
        return

    def transition(self, jump_to=None):
        logger.debug("----------TRIPLE TRANSITION FROM: %s-------------" % self.state)
        if jump_to:
            self.state = jump_to
        else:
            self.state = self.state_transition[self.state]
        logger.debug("----------TRIPLE TRANSITION TO: %s-------------" % self.state)

    state_job = {
        states[__subject]: build_subject,
        states[__predicate]: build_relationship,
        states[__rdfobject]: build_relationship,
        states[__close]: close_pair_or_trip,
        states[__completed]: None,
    }
class Graph():
    start_char= "{"
    end_char = "}"
    default_name = "Default"
    states = ["naming", "populating", "completed"]
    state_transition = {
        "naming": "populating",
        "populating": "completed",
        "completed": None,
    }

    #Graph may or may not contain triples
    def __init__(self, outfile=None):
        self.is_complete = False
        self.triples = 0
        self.name = None
        self.state = self.states[0]
        self.processing = None
        self.outfile = outfile

    def load(self,line):
        #load line into the graph and determine what to do
        #Need to check if graph or triples
        #triples start with <
        #graphs can be names or not, but start with {}, if triple, assume no name.
        #Does line have { or </?
        #Does line end in }
        line = line.strip()
        while line and not self.is_complete:
            line = line.strip()
            #Do work until there is no line remainng
            line = self.state_job[self.state](self,line)
        # if len(self.processing)> 5000: raise ValueError("Graph data incorrect")
        # if len(line.strip()): raise ValueError("didn't parse graph correctly: %d %s" % (len(line),line)) #TODO Figure out why a space is returned
        return line

    def get_incomplete_triple(self):
        """
        Grab the last triple if it's not complete, otherwise grab a new one.
        """
        if self.triples:
            current = self.triples[-1]
            if current.is_complete:
                return Triple()
            else:
                return current
        else:
            return Triple()

    def build_triples(self,line):
        #At this point, the graph has been named and has a line that should be a triple
        #I know the line I get will contain either part of a tripe, or an end char.
        #If it doesn't, something is broke.
        #This step goes on until a } is found.
        triple = self.processing or Triple()
        try:
            line = triple.load(line)
        except TypeError as err:
            logging.warning("Triple loading failed: %s" % err)
            logging.warning("line: %s" % line)

        #Line may be blank or may be a }
        try:
            to_return = line.split(self.end_char, 1)[1]
            self.is_complete = True
            logger.info('GRAPH COMPLETE')
            self.print_to_file(self.end_char)
        except (AttributeError, IndexError) as err:
            to_return = line
        #triple should return a string thats like "} sxxsfdsfaffs" and it shouldn't have more than a single }

        #Load entire line in triple, get a return string if there is one. Presumbably this is the end of the graph only, so lets check
        #consider the case wehre a non triple string gets sent, we don't want to append an empty triples
        #since a split returned some stuff, we can validate that the graph is complete

        if triple.is_complete:
            logger.debug("----APPENDED TRIPLE-----")
            self.print_to_file(triple.to_string(tab=True))
            self.triples += 1
            logger.info("Total triples: %d" % self.triples)
            self.processing = None
        else:
            self.processing = triple
        return to_return

    def set_name(self):
        """
        if any text before starting character, we assume that's the name
        else, it's the default name
        """
        name_str = self.processing.strip()
        self.name = name_str or self.default_name
        self.print_to_file(self.name + '\t ' + self.start_char)
        logger.info("Graph NAME: %s" % self.name)

    def print_to_file(self, line):
        self.outfile.write(line + "\n")

    def get_name(self, line):
        """
        The graph has not started yet, we are still trying to get the name
        # We know that a graph has a name before its first {, so we will build up the string
        # until we reach that point, then process it
        """

        parts = line.split(self.start_char, 1)
        if len(parts) == 1:
            #This means no start char, add to processcing and continue
            self.processing = str(self.processing or "") + parts[0]
            line = None
        else:
            #Start char found, lets set the name and begin the loading trips
            #We have the start char, so we can figure out everything now
            #decipher name
            self.processing = str(self.processing or "") + parts[0]
            self.set_name()
            # print(parts)
            line = parts[1]
            self.transition()
            # self.has_data = True
        return line

    def transition(self):
        #Transition to the next state
        before = self.state
        self.processing = None
        self.state = self.state_transition[self.state]
        after = self.state
        logger.debug("GRAPH STATE TRANSITION %s --> %s" % (before,after))

    state_job = {
        "naming": get_name,
        "populating": build_triples,
        "completed": None,
    }

ignore_chars = ['@','#']
def main(file_path, output_path='cleaned.trig'):
    """
    Assume a TRiG file that has named graphs wrapped in {}
    """
    skipped_lines = []
    graphs = []

    with open(file_path, 'r') as trig, open(output_path, 'w') as outfile:
        graph = Graph(outfile=outfile)
        for line in trig:
            while line:
                logger.debug("Loading Line: %s" % line)
                if line[0] in ignore_chars:
                    skipped_lines.append(line)
                    outfile.write(line)
                line = graph.load(line)
                if graph.is_complete:
                    graphs.append(graph)
                    graph = Graph(outfile=outfile)
    print("------------------------------")
    print("Total graphs found: %s" % len(graphs))
    print("Triples in each graph:")
    for graph in graphs:
        print("%s : %d" % (graph.name, graph.triples))
    print("------------------------------")

if __name__ == "__main__":
    #need file name arg
    fh = logging.FileHandler('log_filename.txt')
    fh.setLevel(logging.CRITICAL)
    fh.setFormatter(formatter)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)

    if len(sys.argv) > 2:
        #Right now, just debug puroses
        if sys.argv[2] == 'debug':
            ch.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    logger.addHandler(ch)
    main(sys.argv[1])
