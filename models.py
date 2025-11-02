from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text, Float
from sqlalchemy.orm import relationship, backref
from database import Base, Session
from cryptography.fernet import Fernet
import os
import datetime

# Load or generate encryption key
key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'encryption_key.key')
if not os.path.exists(key_file):
    key = Fernet.generate_key()
    with open(key_file, 'wb') as f:
        f.write(key)
with open(key_file, 'rb') as f:
    key_data = f.read()
    try:
        cipher = Fernet(key_data)
    except ValueError as e:
        print(f"Invalid encryption key: {e}. Regenerating key...")
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
        cipher = Fernet(key)

def generate_pid():
    """Generate a sequential PID in the format TRY00001, TRY00002, etc."""
    session = Session()
    try:
        # Query the highest PID with prefix 'TRY'
        last_patient = session.query(Patient).filter(Patient.pid.like('TRY%')).order_by(Patient.pid.desc()).first()
        if last_patient and last_patient.pid and last_patient.pid.startswith('TRY'):
            last_number = int(last_patient.pid[3:])  # Extract number after 'TRY'
            next_number = last_number + 1
        else:
            next_number = 1
        pid = f"TRY{next_number:05d}"
        return pid
    finally:
        session.close()

class Patient(Base):
    __tablename__ = 'patients'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    pid = Column(String, unique=True)
    name = Column(String, nullable=False)
    age = Column(Integer)
    gender = Column(String)
    contact = Column(String)
    address = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Configure cascading delete from Patient to Order
    orders = relationship("Order", 
                        back_populates="patient",
                        cascade="all, delete-orphan",
                        passive_deletes=True)

    @property
    def decrypted_name(self):
        try:
            decrypted = cipher.decrypt(self.name.encode()).decode()
            return decrypted
        except Exception as e:
            print(f"Decryption error for patient {self.id} name: {e}")
            return "Decryption Failed"

    @property
    def decrypted_contact(self):
        try:
            return cipher.decrypt(self.contact.encode()).decode() if self.contact else ""
        except Exception as e:
            print(f"Decryption error for patient {self.id} contact: {e}")
            return "Decryption Failed"

    @property
    def decrypted_address(self):
        try:
            return cipher.decrypt(self.address.encode()).decode() if self.address else ""
        except Exception as e:
            print(f"Decryption error for patient {self.id} address: {e}")
            return "Decryption Failed"

    @property
    def decrypted_title(self):
        try:
            return cipher.decrypt(self.title.encode()).decode() if self.title else ""
        except Exception as e:
            print(f"Decryption error for patient {self.id} title: {e}")
            return "Decryption Failed"

    def __repr__(self):
        return f"<Patient(name={self.decrypted_name}, pid={self.pid})>"

class Test(Base):
    __tablename__ = 'tests'
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    department = Column(String)
    rate_inr = Column(Float, default=0.0)
    template = Column(JSON)
    notes = Column(String)

    # Simple backref for orders
    orders = relationship("Order", backref="test")

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey('patients.id', ondelete='CASCADE'), nullable=False)
    test_id = Column(Integer, ForeignKey('tests.id', ondelete='CASCADE'), nullable=False)
    order_date = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default='Pending')
    referring_physician = Column(String)
    payment_method = Column(String)
    discount = Column(Float, default=0.0)
    group_id = Column(Integer)

    # Configure relationships with proper cascading
    patient = relationship("Patient", back_populates="orders")
    results = relationship("Result", 
                         back_populates="order",
                         uselist=False,
                         cascade="all, delete-orphan",
                         passive_deletes=True)
    comments = relationship("OrderComment",
                          cascade="all, delete-orphan",
                          passive_deletes=True)

class Result(Base):
    __tablename__ = 'results'
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, unique=True)
    result_date = Column(DateTime, default=datetime.datetime.utcnow)
    results = Column(JSON)
    notes = Column(String)
    
    # Configure one-to-one relationship with Order
    order = relationship("Order", back_populates="results")

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default='user')

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    entity_type = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    details = Column(Text)
    user = relationship("User")


class ArchiveEntry(Base):
    __tablename__ = 'archive_entries'
    id = Column(Integer, primary_key=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    deleted_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    deleted_at = Column(DateTime, default=datetime.datetime.utcnow)
    data = Column(JSON)
    user = relationship("User")


def _serialize_model(obj):
    """Return a dict of column values for a SQLAlchemy model instance."""
    result = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, datetime.datetime.datetime):
            val = val.isoformat()
        result[col.name] = val
    return result


def archive_patient(session, patient, deleted_by=None):
    """Archive patient and related orders/results/comments into ArchiveEntry.

    This adds an ArchiveEntry to the provided session and flushes it. It does not
    commit the session so the caller can control the transaction (we flush to
    ensure the archive is persisted on commit even if deletion follows).
    """
    payload = {}
    payload['patient'] = _serialize_model(patient)
    payload['orders'] = []
    for order in patient.orders:
        order_dict = _serialize_model(order)
        # attach one-to-one result if present
        if hasattr(order, 'results') and order.results:
            order_dict['result'] = _serialize_model(order.results)
        # attach comments
        comments = []
        if hasattr(order, 'comments') and order.comments:
            for c in order.comments:
                comments.append(_serialize_model(c))
        order_dict['comments'] = comments
        payload['orders'].append(order_dict)

    entry = ArchiveEntry(entity_type='patient', entity_id=patient.id, deleted_by=deleted_by, data=payload)
    session.add(entry)
    # flush so the archive is written when the transaction commits with the deletion
    session.flush()
    return entry

class Location(Base):
    __tablename__ = 'locations'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default='user')

class ReferringPhysician(Base):
    __tablename__ = 'referring_physicians'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default='user')

class OrderTemplate(Base):
    __tablename__ = 'order_templates'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    test_ids = Column(String)

class OrderComment(Base):
    __tablename__ = 'order_comments'
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    comment = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class Package(Base):
    __tablename__ = 'packages'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    test_ids = Column(String)
    description = Column(String)

# Make these available for import
__all__ = ['Base', 'Patient', 'Test', 'Order', 'Result', 'User', 'AuditLog', 
           'Location', 'ReferringPhysician', 'OrderTemplate', 'OrderComment', 
           'Package', 'cipher', 'generate_pid']