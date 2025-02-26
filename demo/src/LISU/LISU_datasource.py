from rdflib import Graph
from typing import List, Any, Optional

# Ontology file path (relative to script root)
ONTOLOGY_ADDRESS = "./data/idoo.owl"

class LisuOntology:
    """Simplified interface for querying LISU ontology data."""
    def __init__(self, vid: str = "", pid: str = "", controller_name: str = ""):
        self.vid = vid
        self.pid = pid
        self.controller_name = controller_name
        self.header = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX lisu: <https://personalpages.manchester.ac.uk/postgrad/mario.sandovalolive/ontology/idoo.owl#>"""

    def _query(self, query_string: str) -> Any:
        """Execute an RDF query on the ontology."""
        graph = Graph()
        try:
            graph.parse(ONTOLOGY_ADDRESS)
            return graph.query(query_string)
        except Exception as e:
            print(f"Failed to query ontology: {e}")
            return []

    def get_controller_attributes(self) -> Optional[dict]:
        """Get basic attributes (name, level) for a specific controller."""
        if not self.vid or not self.pid:
            return None
        query_string = f""" {self.header}
SELECT ?name ?level
WHERE
{{
    ?controller lisu:productName ?name .
    ?controller lisu:VID ?VID .
    ?controller lisu:PID ?PID .
    ?controller lisu:isAppropriate ?level .
    FILTER(?VID = "{self.vid}" && ?PID="{self.pid}")
}}
GROUP BY ?name ?level"""
        result = self._query(query_string)
        for row in result:
            return {"product_name": str(row.name), "level": str(row.level).split("#")[-1]}
        return None

    def get_device_attributes(self) -> List[dict]:
        """Get detailed device attributes for a specific controller."""
        if not self.vid or not self.pid:
            return []
        query_string = f""" {self.header}
SELECT ?name
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
GROUP BY ?name
?x_channel ?x_byte1 ?x_byte2 ?x_scale
?y_channel ?y_byte1 ?y_byte2 ?y_scale
?z_channel ?z_byte1 ?z_byte2 ?z_scale
?pitch_channel ?pitch_byte1 ?pitch_byte2 ?pitch_scale
?roll_channel ?roll_byte1 ?roll_byte2 ?roll_scale
?yaw_channel ?yaw_byte1 ?yaw_byte2 ?yaw_scale
?btn1_channel ?btn1_byte ?btn1_bit
?btn2_channel ?btn2_byte ?btn2_bit"""
        result = self._query(query_string)
        return [{"name": str(row.name), **{k: str(v) for k, v in row.asdict().items() if k != "name"}} for row in result]

    def get_user_modes(self) -> List[str]:
        """Get all user mode macros for a specific controller."""
        if not self.controller_name:
            return []
        query_string = f""" {self.header}
SELECT ?macros
WHERE
{{
    ?controller lisu:productName ?name .
    ?controller lisu:Executes ?actions .
    ?actions lisu:macroName ?macros .
    FILTER(?name = "{self.controller_name}")
}}
GROUP BY ?macros"""
        result = self._query(query_string)
        return [str(row.macros) for row in result]

def ListAllUserModes() -> List[dict]:
    """List all user modes across all controllers."""
    ontology = LisuOntology()
    query_string = f""" {ontology.header}
SELECT ?ctrname ?usrmod
WHERE
{{
    ?controller lisu:productName ?ctrname .
    ?controller lisu:Executes ?actions .
    ?actions lisu:macroName ?usrmod .
}}
GROUP BY ?ctrname ?usrmod
ORDER BY ?usrmod"""
    result = ontology._query(query_string)
    return [{"ctrname": str(row.ctrname), "usrmod": str(row.usrmod)} for row in result]

def ListAllDevices() -> List[dict]:
    """List all devices with basic attributes."""
    ontology = LisuOntology()
    query_string = f""" {ontology.header}
SELECT ?name ?VID ?PID ?level ?AXES ?BTNS ?HATS
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
GROUP BY ?name ?VID ?PID ?level ?AXES ?BTNS ?HATS"""
    result = ontology._query(query_string)
    return [{"name": str(row.name), "VID": str(row.VID), "PID": str(row.PID), 
             "level": str(row.level).split("#")[-1], "AXES": str(row.AXES), 
             "BTNS": str(row.BTNS), "HATS": str(row.HATS)} for row in result]

def ListAllControllers() -> List[dict]:
    """List all controllers with detailed attributes."""
    ontology = LisuOntology()
    query_string = f""" {ontology.header}
SELECT ?name ?VID ?PID ?level ?AXES ?BTNS ?HATS
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
GROUP BY ?name ?VID ?PID ?level ?AXES ?BTNS ?HATS
?leftTriggerIdx ?rightTriggerIdx
?leftStickLRIdx ?leftStickUDIdx
?rightStickLRIdx ?rightStickUDIdx
?leftBtn1Idx ?rightBtn1Idx
?leftBtn2Idx ?rightBtn2Idx
?hatLeftIdx ?hatRightIdx ?hatUpIdx ?hatDownIdx ?hatIdx
?selectBtnIdx ?startBtnIdx ?triangleBtnIdx ?squareBtnIdx ?circleBtnIdx ?crossXBtnIdx"""
    result = ontology._query(query_string)
    return [{k: str(v) for k, v in row.asdict().items()} for row in result]

if __name__ == "__main__":
    # Example usage
    ontology = LisuOntology(vid="054c", pid="09cc")  # PS4 controller example
    attrs = ontology.get_controller_attributes()
    if attrs:
        print(f"Controller: {attrs['product_name']}, Level: {attrs['level']}")
