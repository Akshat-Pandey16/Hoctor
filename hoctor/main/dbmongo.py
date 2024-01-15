from pymongo import MongoClient
def get_database():
 
   # Provide the mongodb atlas url to connect python to mongodb using pymongo
   CONNECTION_STRING = "mongodb+srv://sanskardwivedi003:hashsociety@Localhive.jdofuju.mongodb.net/ech?retryWrites=true&w=majority"
 
   # Create a connection using MongoClient. You can import MongoClient or use pymongo.MongoClient
   client = MongoClient(CONNECTION_STRING)
 
   # Create the database for our example (we will use the same database throughout the tutorial
   return client['ech']
  
# This is added so that many files can reuse the function get_database()
if __name__ == "__main__":   
  
   # Get the database
   dbname = get_database()
   print(dbname)
   dbname = get_database()
   collection_name = dbname["ech"]
   item_1={
      "name" : ""
   }
   collection_name.insert_many([item_1])



