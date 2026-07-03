import hashlib
from typing import Annotated
from fastapi import HTTPException

def genrate_password_hash (password:Annotated[str,None]) -> str :
    """Create password hash"""
    if not password :
        raise HTTPException(501,"Error hash password")
    
    hash_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return hash_password

def chick_password (hashedPassword:Annotated[str,None],password:Annotated[str,None]) -> bool :
    if not hashedPassword and not password :
        raise HTTPException(501,"Error Chick password")
    
    hash_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    if hashedPassword == hash_password :
        return True
    
    return False

    
    
    
    
    
    
    
    
    
    