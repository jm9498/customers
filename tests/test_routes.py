""" 
Customer API Service Test Suite

Test cases can be run with the following:
nosetests -v --with-spec --spec-color
coverage report -m
codecov -token=$CODECOV_TOKEN

While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_routes.py:TestCustomerServer
"""

from http.client import responses
import os
import logging
import unittest

# from unittest.mock import MagicMock, patch
from urllib.parse import quote_plus
from service import app, status
from service.models import db, init_db
from .factories import CustomerFactory

# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
#logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/testdb"
)
BASE_URL = "/customers"
CONTENT_TYPE_JSON = "application/json"


######################################################################
#  T E S T   C A S E S
######################################################################
class TestCustomerServer(unittest.TestCase):
    """ Customer API Server Tests """

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        db.drop_all()  # clean up the last tests
        db.create_all()  # create new tables
        self.app = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_customers(self, count):
        """Factory method to create customers in bulk"""
        customers = []
        for _ in range(count):
            test_customer = CustomerFactory()
            resp = self.app.post(
                BASE_URL, json=test_customer.serialize(), content_type=CONTENT_TYPE_JSON
            )
            self.assertEqual(
                resp.status_code, status.HTTP_201_CREATED, "Could not create test customer"
            )
            new_customer = resp.get_json()
            test_customer.id = new_customer["id"]
            customers.append(test_customer)
        return customers

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """ Test index call """
        resp = self.app.get("/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["name"], "Customer Service")

    # Test create customer account
    def test_create_a_customer(self):
        """Create a new Customer Account"""
        test_customer = CustomerFactory()
        logging.debug(test_customer)
        resp = self.app.post(
            BASE_URL, json=test_customer.serialize(), content_type=CONTENT_TYPE_JSON
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        # Make sure location header is set
        location = resp.headers.get("Location", None)
        self.assertIsNotNone(location)
        # Check the data is correct
        new_customer = resp.get_json()
        self.assertEqual(new_customer["first_name"], test_customer.first_name,"First name does not match")
        self.assertEqual(new_customer["last_name"], test_customer.last_name, "Last name does not match")
        self.assertEqual(new_customer["email"], test_customer.email, "Email does not match")
        self.assertEqual(new_customer["phone_number"], test_customer.phone_number, "Phone number does not match")

# Check that the location header was correct
        resp = self.app.get(location, content_type=CONTENT_TYPE_JSON)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        new_customer = resp.get_json()
        self.assertEqual(new_customer["first_name"], test_customer.first_name,"First name does not match")
        self.assertEqual(new_customer["last_name"], test_customer.last_name, "Last name does not match")
        self.assertEqual(new_customer["email"], test_customer.email, "Email does not match")
        self.assertEqual(new_customer["phone_number"], test_customer.phone_number, "Phone number does not match")



    #Test create customer account with missing data
    def test_create_a_customer_no_data(self):
        """Create a Customer with missing data"""
        resp = self.app.post(BASE_URL, json={}, content_type=CONTENT_TYPE_JSON)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

  # Test update the customer
    def test_update_customer(self):
        """Update an existing customer"""
        # create a customer to update
        test_customer = CustomerFactory()
        resp = self.app.post(
            BASE_URL, json=test_customer.serialize(), content_type=CONTENT_TYPE_JSON
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # update the customer
        new_customer = resp.get_json()
        logging.debug(new_customer)
        new_customer["email"] = "new@email.com"
        resp = self.app.put(
            "/customers/{}".format(new_customer["id"]),
            json=new_customer,
            content_type=CONTENT_TYPE_JSON,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        updated_customer = resp.get_json()
        logging.debug(updated_customer)
        self.assertEqual(updated_customer["email"], "new@email.com")

    def test_get_customer_list(self):
        """Get a list of Customers"""
        self.create_customers(5)
        resp = self.app.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 5)

    def test_get_customer(self):
        """Get a single customer"""
        # get the id of a customer
        test_customer = self.create_customers(1)[0]
        resp = self.app.get(
            "/customers/{}".format(test_customer.id), content_type=CONTENT_TYPE_JSON
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["first_name"], test_customer.first_name)

    def test_get_customer_not_found(self):
        """Get a customer thats not found"""
        resp = self.app.get("/customers/0")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


    def test_query_customer_list_by_email(self):
        """Query Customers by Email"""
        customers = self.create_customers(10)
        test_email = customers[0].email
        email_customers = [customer for customer in customers if customer.email == test_email]
        resp = self.app.get(
            BASE_URL, query_string="email={}".format(quote_plus(test_email))
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), len(email_customers))
        # check the data just to be sure
        for customer in data:
            self.assertEqual(customer["email"], test_email)

    def test_query_customer_list_by_last_name(self):
        """Query Customers by last_name"""
        customers = self.create_customers(10)
        test_last_name = customers[0].last_name
        last_name_customers = [customer for customer in customers if customer.last_name == test_last_name]
        resp = self.app.get(
            BASE_URL, query_string="last_name={}".format(quote_plus(test_last_name))
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), len(last_name_customers))
        # check the data just to be sure
        for customer in data:
            self.assertEqual(customer["last_name"], test_last_name)

    def test_create_customer_no_content_type(self):
        """Create a customer with no content type"""
        resp = self.app.post(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # Test delete customer
    def test_delete_customer(self):
        """Delete a Customer"""
        test_customer = self.create_customers(1)[0]
        resp = self.app.delete(
            "{0}/{1}".format(BASE_URL, test_customer.id), content_type=CONTENT_TYPE_JSON
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(resp.data), 0)
        # make sure they are deleted
        resp = self.app.get(
            "{0}/{1}".format(BASE_URL, test_customer.id), content_type=CONTENT_TYPE_JSON
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

