import mysql.connector
from datetime import datetime, timedelta
import csv

# Database initialization
conn = mysql.connector.connect(
    host='127.0.0.1',
    user='root',
    password='1234@Cofee',
    database='leave_management'
)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        leave_balance INT NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS leave_requests (
        id INT AUTO_INCREMENT PRIMARY KEY,
        employee_id INT,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        status VARCHAR(255) DEFAULT 'Pending',
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
''')

conn.commit()

# Function to read manager data from a text file
def read_manager_data(filename='manager_data.txt'):
    try:
        with open(filename, 'r') as file:
            manager_data = {}
            for line in file:
                name, manager_id = line.strip().split(',')
                manager_data[name] = int(manager_id)
            return manager_data
    except FileNotFoundError:
        print(f"File {filename} not found. Manager validation will not be performed.")
        return {}

class Employee:

    def __init__(self, id, name, leave_balance=20):
        self.id = id
        self.name = name
        self.leave_balance = leave_balance

    @classmethod
    def create_employee(cls, name, leave_balance=20):
        if not (0 <= leave_balance <= 20):
            raise ValueError("Leave balance must be between 0 and 20.")
        cursor.execute('INSERT INTO employees (name, leave_balance) VALUES (%s, %s)', (name, leave_balance))
        conn.commit()
        employee_id = cursor.lastrowid
        print(f"Employee {name} (ID: {employee_id}) created successfully.")
        return cls(employee_id, name, leave_balance)

    def apply_leave(self, start_date, end_date):
        try:
            start_date = datetime.strptime(start_date, '%d-%m-%Y').date()
            end_date = datetime.strptime(end_date, '%d-%m-%Y').date()

            today = datetime.now().date()
            if start_date < today or end_date < today:
                raise ValueError("Leave dates must be in the future.")

            if start_date > end_date:
                raise ValueError("End date should be equal to or after the start date.")

            leave_days = (end_date - start_date).days + 1

            if leave_days > self.leave_balance:
                raise ValueError(f"Not enough leave balance. Available: {self.leave_balance} days.")

            cursor.execute(
                'INSERT INTO leave_requests (employee_id, start_date, end_date) VALUES (%s, %s, %s)',
                (self.id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            conn.commit()
            print(
                f"Leave request from {start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')} submitted successfully."
            )
        except ValueError as e:
            print(f"Error: {e}")

    def view_leave_balance(self):
        print(f"{self.name}'s leave balance: {self.leave_balance} days")

    @classmethod
    def get_all_employees(cls):
        cursor.execute('SELECT * FROM employees')
        return cursor.fetchall()

class Manager(Employee):
    manager_data = read_manager_data()

    def __init__(self, id, name, leave_balance=20):
        super().__init__(id, name, leave_balance)
        if self.id not in Manager.manager_data.values():
            raise ValueError("Manager validation failed. Invalid manager ID.")

    @classmethod
    def get_manager_id(cls, manager_name):
        return cls.manager_data.get(manager_name)

    @classmethod
    def create_manager(cls, name, leave_balance=20):
        manager_names = read_manager_data().keys()
        if name not in manager_names:
            with open('manager_data.txt', 'a') as file:
                file.write(f"{name},{cursor.lastrowid}\n")
            manager_names.add(name)
            cursor.execute(
                'INSERT INTO employees (name, leave_balance) VALUES (%s, %s)',
                (name, leave_balance))
            conn.commit()
            manager_id = cursor.lastrowid
            print(f"Manager {name} (ID: {manager_id}) created successfully.")
            return cls(manager_id, name, leave_balance)
        else:
            raise ValueError("Manager with this name already exists.")

    @classmethod
    def approve_leave(cls, request_id):
    
        cursor.execute(
            'SELECT * FROM leave_requests WHERE id = %s AND status = %s',
            (request_id, 'Pending')
        )
        leave_request = cursor.fetchone()

        if leave_request:
            _, employee_id, start_date, end_date, _ = leave_request
            
            leave_days = (end_date - start_date).days + 1

            cursor.execute('SELECT * FROM employees WHERE id = %s', (employee_id,))
            employee = cursor.fetchone()

            if employee:
                _, _, current_leave_balance = employee
                new_leave_balance = max(0, current_leave_balance - leave_days)
            
                cursor.execute('UPDATE employees SET leave_balance = %s WHERE id = %s', (new_leave_balance, employee_id))
                conn.commit()

                cursor.execute('UPDATE leave_requests SET status = %s WHERE id = %s', ('Approved', request_id))
                conn.commit()

                print(f"Leave request {request_id} approved successfully.")
            else:
                print(f"Employee with ID {employee_id} not found.")
        else:
            print(f"Leave request {request_id} not found or not in Pending status.")



    def reject_leave(cls, request_id):
    
        cursor.execute(
        'SELECT * FROM leave_requests WHERE id = %s AND status = %s',
        (request_id, 'Pending')
        )
        leave_request = cursor.fetchone()

        if leave_request:
            cursor.execute('UPDATE leave_requests SET status = %s WHERE id = %s', ('Rejected', request_id))
            conn.commit()
            print(f"Leave request {request_id} rejected successfully.")
        else:
            print(f"Leave request {request_id} not found or not in Pending status.")

    @classmethod
    def delete_leave_request(cls, request_id):
    
        cursor.execute(
        'SELECT * FROM leave_requests WHERE id = %s AND status IN (%s, %s, %s)',
            (request_id, 'Pending', 'Approved', 'Rejected')
        )
        leave_request = cursor.fetchone()

        if leave_request:
            _, employee_id, start_date, end_date, _ = leave_request
            7
            leave_days = (end_date - start_date).days + 1

            cursor.execute('SELECT * FROM employees WHERE id = %s', (employee_id,))
            employee = cursor.fetchone()

            if employee:
                _, _, current_leave_balance = employee
                new_leave_balance = max(0, current_leave_balance + leave_days)
                cursor.execute('UPDATE employees SET leave_balance = %s WHERE id = %s', (new_leave_balance, employee_id))
                conn.commit()

                print(
                f"{leave_days} days added back to employee's leave balance. New balance: {new_leave_balance} days."
                )
            
                cursor.execute('DELETE FROM leave_requests WHERE id = %s', (request_id,))
                conn.commit()
                print(f"Leave request {request_id} deleted successfully.")
            else:
                print(f"Employee with ID {employee_id} not found.")
        else:
            print(f"Leave request {request_id} not found or not in Pending, Approved, or Rejected status.")


    @classmethod
    def view_leave_requests(cls, status='Pending'):
        cursor.execute('SELECT * FROM leave_requests WHERE status = %s', (status,))
        requests = cursor.fetchall()
        return requests

# User interaction
while True:
  print("\nLeave Management System Menu:")
  print("1. Create Employee")
  print("2. Apply for Leave")
  print("3. View Leave Balance")
  print("4. View Pending Leave Requests")
  print("5. Approve Leave Request (Manager)")
  print("6. Reject Leave Request (Manager)")
  print("7. Delete Leave Request (Manager)")
  print("8. Exit")

  choice = input("Enter your choice (1-8): ")

  if choice == '1':
    name = input("Enter employee name: ")
    leave_balance = int(
        input("Enter leave balance (0-20, default is 20): ") or 20)
    try:
      Employee.create_employee(name, leave_balance)
    except ValueError as e:
      print(f"Error: {e}")

  elif choice == '2':
    employee_id = int(input("Enter your employee ID: "))
    start_date_str = input("Enter start date (DD-MM-YYYY): ")
    end_date_str = input("Enter end date (DD-MM-YYYY): ")

    try:
      start_date = datetime.strptime(start_date_str, '%d-%m-%Y').date()
      end_date = datetime.strptime(end_date_str, '%d-%m-%Y').date()
      today = datetime.now().date()

      if start_date < today or end_date < today:
        raise ValueError("Leave dates must be in the future.")

      if start_date > end_date:
        raise ValueError(
            "End date should be equal to or after the start date.")

      employee = Employee.get_all_employees()[employee_id - 1]
      employee = Employee(*employee)
      employee.apply_leave(start_date_str, end_date_str)

    except ValueError as e:
      print(f"Error: {e}")

  elif choice == '3':
    employee_id = int(input("Enter your employee ID: "))
    employee = Employee.get_all_employees()[employee_id - 1]
    employee = Employee(*employee)
    employee.view_leave_balance()

  elif choice == '4':
    pending_requests = Manager.view_leave_requests()
    if pending_requests:
      print("\nPending Leave Requests:")
      for request in pending_requests:
        print(request)
    else:
      print("No pending leave requests.")

  elif choice in ('5', '6', '7'):
    manager_name = input("Enter your manager name: ")
    manager_id = Manager.get_manager_id(manager_name)
    if manager_id is not None:
      manager = Manager.get_all_employees()[manager_id - 1]
      manager = Manager(*manager)

      # Display pending leave requests
      pending_requests = manager.view_leave_requests()
      if pending_requests:
        print("\nPending Leave Requests:")
        for request in pending_requests:
          print(request)

        request_id = int(input("Enter leave request ID to process: "))

        if choice == '5':
          manager.approve_leave(request_id)
        elif choice == '6':
          manager.reject_leave(request_id)
        elif choice == '7':
          manager.delete_leave_request(request_id)

      else:
        print("No pending leave requests.")
    else:
      print("Invalid manager name. Please enter a valid manager name.")

  elif choice == '8':
    # Exiting the loop without breaking it
    break

  else:
    print("Invalid choice. Please enter a number between 1 and 8.")


    pending_requests = Manager.view_leave_requests()
    with open('leave_requests.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([   "ID", "Employee ID", "Start Date", "End Date", "Status"])
        for request in pending_requests:
            writer.writerow(request)

print("Exiting Leave Management System. Goodbye!")
