import re
from rdflib import *

address = "C:/Users/mso_2/OneDrive - The University of Manchester/Documents/GitHub/LISU v3.2/Data/idoo.owl"
#address = "P:/public_html/ontology/idoo.owl"

class OntCtrlManager:
    def __init__(self, Controller):
        self.vid = Controller.vid
        self.pid = Controller.pid
        self.header = Controller.header

        q = Controller.ControllerAttributes()
        for row in q:
            self.productName = str(row.name)
            self.level = re.sub(r'.*#', '#', str(row.level)).replace("#","")

class OntCtrl:
    def __init__(self, vid, pid):
        self.vid = vid
        self.pid = pid
        self.header = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX lisu: <https://personalpages.manchester.ac.uk/postgrad/mario.sandovalolive/ontology/idoo.owl#>"""

    def ControllerAttributes(self):
        graph = Graph()
        graph.parse(address)

        query_string = """ %s
        SELECT ?controller ?level ?name ?VID ?PID
        WHERE
        {
        ?controller lisu:productName ?name  .
        ?controller lisu:VID ?VID .
        ?controller lisu:PID ?PID .
        ?controller lisu:isAppropriate ?level .
        FILTER(?VID = "%s" && ?PID="%s")
        }
        GROUP BY ?controller ?level ?name ?VID ?PID""" % (self.header, self.vid, self.pid)

        _query = graph.query(query_string)
        return _query

    def LisuDeviceAttributes(self):
        graph = Graph()
        graph.parse(address)
        #graph.parse("C:/Users/mso_2/OneDrive - The University of Manchester/Documents/LISU - Docs/Ontologies/idoo.owl")

        #qstring = "VID= %s, PID= %s" % (self.vid, self.pid)
        #print(qstring)

        query_string = """ %s
        SELECT ?controller ?name ?VID ?PID
        ?x_channel ?x_byte1 ?x_byte2 ?x_scale
        ?y_channel ?y_byte1 ?y_byte2 ?y_scale
        ?z_channel ?z_byte1 ?z_byte2 ?z_scale
        ?pitch_channel ?pitch_byte1 ?pitch_byte2 ?pitch_scale
        ?roll_channel ?roll_byte1 ?roll_byte2 ?roll_scale
        ?yaw_channel ?yaw_byte1 ?yaw_byte2 ?yaw_scale
        ?btn1_channel ?btn1_byte ?btn1_bit
        ?btn2_channel ?btn2_byte ?btn2_bit
        WHERE
        {
        ?controller lisu:productName ?name  .
        ?controller lisu:VID ?VID .
        ?controller lisu:PID ?PID .
        ?controller lisu:x_channel ?x_channel .
        ?controller lisu:x_byte1 ?x_byte1 .
        ?controller lisu:x_byte2 ?x_byte2 .
        ?controller lisu:x_scale ?x_scale .
        ?controller lisu:y_channel ?y_channel .
        ?controller lisu:y_byte1 ?y_byte1 .
        ?controller lisu:y_byte2 ?y_byte2 .
        ?controller lisu:y_scale ?y_scale .
        ?controller lisu:z_channel ?z_channel .
        ?controller lisu:z_byte1 ?z_byte1 .
        ?controller lisu:z_byte2 ?z_byte2 .
        ?controller lisu:z_scale ?z_scale .
        ?controller lisu:pitch_channel ?pitch_channel .
        ?controller lisu:pitch_byte1 ?pitch_byte1 .
        ?controller lisu:pitch_byte2 ?pitch_byte2 .
        ?controller lisu:pitch_scale ?pitch_scale .
        ?controller lisu:roll_channel ?roll_channel .
        ?controller lisu:roll_byte1 ?roll_byte1 .
        ?controller lisu:roll_byte2 ?roll_byte2 .
        ?controller lisu:roll_scale ?roll_scale .
        ?controller lisu:yaw_channel ?yaw_channel .
        ?controller lisu:yaw_byte1 ?yaw_byte1 .
        ?controller lisu:yaw_byte2 ?yaw_byte2 .
        ?controller lisu:yaw_scale ?yaw_scale .
        ?controller lisu:btn1_channel ?btn1_channel .
        ?controller lisu:btn1_byte ?btn1_byte .
        ?controller lisu:btn1_bit ?btn1_bit .
        ?controller lisu:btn2_channel ?btn2_channel .
        ?controller lisu:btn2_byte ?btn2_byte .
        ?controller lisu:btn2_bit ?btn2_bit .
        FILTER(?VID = "%s" && ?PID="%s")
        }
        GROUP BY ?controller ?name ?VID ?PID
        ?x_channel ?x_byte1 ?x_byte2 ?x_scale
        ?y_channel ?y_byte1 ?y_byte2 ?y_scale
        ?z_channel ?z_byte1 ?z_byte2 ?z_scale
        ?pitch_channel ?pitch_byte1 ?pitch_byte2 ?pitch_scale
        ?roll_channel ?roll_byte1 ?roll_byte2 ?roll_scale
        ?yaw_channel ?yaw_byte1 ?yaw_byte2 ?yaw_scale
        ?btn1_channel ?btn1_byte ?btn1_bit
        ?btn2_channel ?btn2_byte ?btn2_bit

        """ % (self.header, self.vid, self.pid)

        #print(query_string)
        _query = graph.query(query_string)
        return _query

class UsrModsManager:
    def __init__(self,controller_name):
        self.controller_name = controller_name
        self.header = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX lisu: <https://personalpages.manchester.ac.uk/postgrad/mario.sandovalolive/ontology/idoo.owl#>"""

    def GetAllUserModes(self):
        list_macros = []

        graph = Graph()
        graph.parse(address)
        #graph.parse("C:/Users/mso_2/OneDrive - The University of Manchester/Documents/LISU - Docs/Ontologies/idoo.owl")

        query_string = """ %s
        SELECT ?controller ?actions ?level ?macros ?name
        WHERE
        {
        ?controller lisu:productName ?name  .
        ?controller lisu:Executes ?actions.
        ?controller lisu:isAppropriate ?level .
        ?actions lisu:macroName ?macros .
        FILTER(?name = "%s")
        }
        GROUP BY ?controller ?actions ?macros ?name ?level""" % (self.header, self.controller_name)

        _query = graph.query(query_string)

        for row in _query:
            list_macros.append(row.macros)

        return list_macros

# Retrieve all the information
def ListAllUserModes():
    graph = Graph()
    graph.parse(address)
    #graph.parse("C:/Users/mso_2/OneDrive - The University of Manchester/Documents/LISU - Docs/Ontologies/idoo.owl")

    query_string = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX lisu: <https://personalpages.manchester.ac.uk/postgrad/mario.sandovalolive/ontology/idoo.owl#>
    SELECT ?controller ?actions ?ctrname ?usrmod
        WHERE
        {
        ?controller lisu:productName ?ctrname  .
        ?controller lisu:Executes ?actions.
        ?actions lisu:macroName ?usrmod .

        }
        GROUP BY ?controller ?actions ?ctrname ?usrmod
        ORDER BY ?usrmod
    """
    _query = graph.query(query_string)
    return _query


def ListAllDevices():
    graph = Graph()
    graph.parse(address)
    #graph.parse("C:/Users/mso_2/OneDrive - The University of Manchester/Documents/LISU - Docs/Ontologies/idoo.owl")

    query_string = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX lisu: <https://personalpages.manchester.ac.uk/postgrad/mario.sandovalolive/ontology/idoo.owl#>

        SELECT ?controller ?name ?VID ?PID ?level ?AXES ?BTNS ?HATS
        WHERE
            {
                ?controller lisu:productName ?name  .
                ?controller lisu:VID ?VID .
                ?controller lisu:PID ?PID .
                ?controller lisu:isAppropriate ?level .
                ?controller lisu:DOF ?AXES .
                ?controller lisu:BTNS ?BTNS .
                ?controller lisu:HATS ?HATS .
            }
        GROUP BY  ?controller ?name ?VID ?PID ?level ?AXES ?BTNS ?HATS

    """

    _query = graph.query(query_string)
    return _query


def ListAllControllers():
    graph = Graph()
    graph.parse(address)
    #graph.parse("C:/Users/mso_2/OneDrive - The University of Manchester/Documents/LISU - Docs/Ontologies/idoo.owl")

    query_string = """ PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX lisu: <https://personalpages.manchester.ac.uk/postgrad/mario.sandovalolive/ontology/idoo.owl#>

    SELECT ?controller ?name ?VID ?PID ?level ?AXES ?BTNS ?HATS
    ?leftTriggerIdx ?rightTriggerIdx
    ?leftStickLRIdx ?leftStickUDIdx
    ?rightStickLRIdx ?rightStickUDIdx
    ?leftBtn1Idx ?rightBtn1Idx
    ?leftBtn2Idx ?rightBtn2Idx
    ?hatLeftIdx ?hatRightIdx ?hatUpIdx ?hatDownIdx ?hatIdx
    ?selectBtnIdx ?startBtnIdx ?triangleBtnIdx ?squareBtnIdx ?circleBtnIdx ?crossXBtnIdx

    WHERE
    {
       ?controller lisu:productName ?name  .
       ?controller lisu:VID ?VID .
       ?controller lisu:PID ?PID .
       ?controller lisu:isAppropriate ?level .
       ?controller lisu:DOF ?AXES .
       ?controller lisu:BTNS ?BTNS .
       ?controller lisu:HATS ?HATS .
       ?controller lisu:leftTriggerIdx ?leftTriggerIdx .
       ?controller lisu:rightTriggerIdx ?rightTriggerIdx .
       ?controller lisu:leftStickLRIdx ?leftStickLRIdx .
       ?controller lisu:leftStickUDIdx ?leftStickUDIdx .
       ?controller lisu:rightStickLRIdx ?rightStickLRIdx .
       ?controller lisu:rightStickUDIdx ?rightStickUDIdx .
       ?controller lisu:leftBtn1Idx ?leftBtn1Idx .
       ?controller lisu:rightBtn1Idx ?rightBtn1Idx .
       ?controller lisu:leftBtn2Idx ?leftBtn2Idx .
       ?controller lisu:rightBtn2Idx ?rightBtn2Idx .
       ?controller lisu:hatLeftIdx ?hatLeftIdx .
       ?controller lisu:hatRightIdx ?hatRightIdx .
       ?controller lisu:hatUpIdx ?hatUpIdx .
       ?controller lisu:hatDownIdx ?hatDownIdx .
       ?controller lisu:hatIdx ?hatIdx .
       ?controller lisu:selectBtnIdx ?selectBtnIdx .
       ?controller lisu:startBtnIdx ?startBtnIdx .
       ?controller lisu:triangleBtnIdx ?triangleBtnIdx .
       ?controller lisu:squareBtnIdx ?squareBtnIdx .
       ?controller lisu:circleBtnIdx ?circleBtnIdx .
       ?controller lisu:crossXBtnIdx ?crossXBtnIdx .
    }
    GROUP BY  ?controller ?name ?VID ?PID ?level ?AXES ?BTNS ?HATS
    ?leftTriggerIdx ?rightTriggerIdx
    ?leftStickLRIdx ?leftStickUDIdx
    ?rightStickLRIdx ?rightStickUDIdx
    ?leftBtn1Idx ?rightBtn1Idx
    ?leftBtn2Idx ?rightBtn2Idx
    ?hatLeftIdx ?hatRightIdx ?hatUpIdx ?hatDownIdx ?hatIdx
    ?selectBtnIdx ?startBtnIdx ?triangleBtnIdx ?squareBtnIdx ?circleBtnIdx ?crossXBtnIdx
    """
    _query = graph.query(query_string)
    return _query
