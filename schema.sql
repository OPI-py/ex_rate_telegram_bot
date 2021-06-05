DROP TABLE IF EXISTS rates; /*this deletes any already existing tables named posts so you don't get confusing behavior*/

CREATE TABLE rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    currency TEXT Not NULL,
    currency_value TEXT Not NULL);