from pydantic import BaseModel,Field

class MembershipDetails (BaseModel):
    Price:float
    duration_months:str
    walk_machine:bool
    deduct:str
    description:str