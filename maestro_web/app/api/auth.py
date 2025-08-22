from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt # <--- ADICIONEI 'jwt' AQUI
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models import models, schemas
from ..core import security

# O resto do arquivo permanece exatamente o mesmo...

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
router = APIRouter(prefix="/auth", tags=["Autenticação"])

@router.post("/register", response_model=schemas.User)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Registra um novo usuário."""
    db_user = db.query(models.Usuario).filter(models.Usuario.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="E-mail já registrado")
    
    hashed_password = security.get_password_hash(user.password)
    
    new_user = models.Usuario(
        email=user.email,
        nome_completo=user.nome_completo,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Gera um token de acesso para o usuário."""
    user = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()

    # --- LÓGICA DE VERIFICAÇÃO CORRIGIDA E MAIS ROBUSTA ---
    # 1. Verifica se o usuário existe E se ele tem uma senha cadastrada.
    # 2. SÓ DEPOIS, verifica se a senha fornecida está correta.
    # A ordem é importante por causa do "short-circuiting" do Python.
    if not user or not user.hashed_password or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # --- FIM DA CORREÇÃO ---
    
    access_token = security.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Decodifica o token e retorna o usuário atual."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.Usuario).filter(models.Usuario.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user