from rdflib import Graph
from typing import List, Any

# Ontology file path (relative to script root)
ONTOLOGY_ADDRESS = "./idoo.owl"

class OntCtrlManager:
    """Manages controller attributes retrieved from ontology."""
    def __init__(self, controller: 'OntCtrl'):
        self.vid = controller.vid
        self.pid = controller.pid
        self.header = controller.header
        for row in controller.ControllerAttributes():
            self.product_name = str(row.name)
            self.level = str(row.level).split("#")[-1]  # Extract fragment after '#'

class OntCtrl:
    """Handles ontology queries for controller and device attributes."""
    def __init__(self, vid: str, pid: str):
        self.vid = vid
        self.pid = pid
        self.header = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX lisu: <https://personalpages.manchester.ac.uk/postgrad/mario.sandovalolive/ontology/idoo.owl#>"""

    def ControllerAttributes(self) -> Any:
        """Query basic controller attributes (name, level)."""
        graph = Graph()
        graph.parse(ONTOLOGY_ADDRESS)
        query_string = f""" {self.header}
SELECT ?controller ?level ?name ?VID ?PID
WHERE
{{
    ?controller lisu:productName ?name .
    ?controller lisu:VID ?VID .
    ?controller lisu:PID ?PID .
    ?controller lisu:isAppropriate ?level .
    FILTER(?VID = "{self.vid}" && ?PID="{self.pid}")
}}
GROUP BY ?controller ?level ?name ?VID ?PID"""
        return graph.query(query_string)

    def LisuDeviceAttributes(self) -> Any:
        """Query detailed device attributes (channels, bytes, scales)."""
        graph = Graph()
        graph.parse(ONTOLOGY_ADDRESS)
        query_string = f""" {self.header}
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
{{
    ?controller lisu:productName ?name .
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
    FILTER(?VID = "{self.vid}" && ?PID="{self.pid}")
}}
GROUP BY ?controller ?name ?VID ?PID
?x_channel ?x_byte1 ?x_byte2 ?x_scale
?y_channel ?y_byte1 ?y_byte2 ?y_scale
?z_channel ?z_byte1 ?z_byte2 ?z_scale
?pitch_channel ?pitch_byte1 ?pitch_byte2 ?pitch_scale
?roll_channel ?roll_byte1 ?roll_byte2 ?roll_scale
?yaw_channel ?yaw_byte1 ?yaw_byte2 ?yaw_scale
?btn1_channel ?btn1_byte ?btn1_bit
?btn2_channel ?btn2_byte ?btn2_bit"""
        return graph.query(query_string)

class UsrModsManager:
    """Manages user mode macros for a controller."""
    def __init__(self, controller_name: str):
        self.controller_name = controller_name
        self.header = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX lisu: <https://personalpages.manchester.ac.uk/postgrad/mario.sandovalolive/ontology/idoo.owl#>"""

    def GetAllUserModes(self) -> List[str]:
        """Retrieve all user mode macros for the controller."""
        graph = Graph()
        graph.parse(ONTOLOGY_ADDRESS)
        query_string = f""" {self.header}
SELECT ?controller ?actions ?level ?macros ?name
WHERE
{{
    ?controller lisu:productName ?name .
    ?controller lisu:Executes ?actions .
    ?controller lisu:isAppropriate ?level .
    ?actions lisu:macroName ?macros .
    FILTER(?name = "{self.controller_name}")
}}
GROUP BY ?controller ?actions ?macros ?name ?level"""
        query = graph.query(query_string)
        return [str(row.macros) for row in query]

def ListAllUserModes() -> Any:
    """List all user modes across all controllers."""
    graph = Graph()
    graph.parse(ONTOLOGY_ADDRESS)
    query_string = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX lisu: <https://personalpages.manchester.ac.uk/postgrad/mario.sandovalolive/ontology/idoo.owl#>
SELECT ?controller ?actions ?ctrname ?usrmod
WHERE
{{
    ?controller lisu:productName ?ctrname .
    ?controller lisu:Executes ?actions .
    ?actions lisu:macroName ?usrmod .
}}
GROUP BY ?controller ?actions ?ctrname ?usrmod
ORDER BY ?usrmod"""
    return graph.query(query_string)

def ListAllDevices() -> Any:
    """List all devices with basic attributes."""
    graph = Graph()
    graph.parse(ONTOLOGY_ADDRESS)
    query_string = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX lisu: <https://personalpages.manchester.ac.uk/postgrad/mario.sandovalolive/ontology/idoo.owl#>
SELECT ?controller ?name ?VID ?PID ?level ?AXES ?BTNS ?HATS
WHERE
{{
    ?controller lisu:productName ?name .
    ?controller lisu:VID ?VID .
    ?controller lisu:PID ?PID .
    ?controller lisu:isAppropriate ?level .
    ?controller lisu:DOF ?AXES .
    ?controller lisu:BTNS ?BTNS .
    ?controller lisu:HATS ?HATS .
}}
GROUP BY ?controller ?name ?VID ?PID ?level ?AXES ?BTNS ?HATS"""
    return graph.query(query_string)

def ListAllControllers() -> Any:
    """List all controllers with detailed attributes."""
    graph = Graph()
    graph.parse(ONTOLOGY_ADDRESS)
    query_string = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
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
{{
    ?controller lisu:productName ?name .
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
}}
GROUP BY ?controller ?name ?VID ?PID ?level ?AXES ?BTNS ?HATS
?leftTriggerIdx ?rightTriggerIdx
?leftStickLRIdx ?leftStickUDIdx
?rightStickLRIdx ?rightStickUDIdx
?leftBtn1Idx ?rightBtn1Idx
?leftBtn2Idx ?rightBtn2Idx
?hatLeftIdx ?hatRightIdx ?hatUpIdx ?hatDownIdx ?hatIdx
?selectBtnIdx ?startBtnIdx ?triangleBtnIdx ?squareBtnIdx ?circleBtnIdx ?crossXBtnIdx"""
    return graph.query(query_string)

if __name__ == "__main__":
    # Example usage
    ctrl = OntCtrl("054c", "09cc")  # Example VID/PID (PS4 controller)
    for row in ctrl.ControllerAttributes():
        print(f"Controller: {row.name}, Level: {row.level}")
