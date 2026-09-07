# Reference README format (follow this structure exactly)

Use the generated file paths, schemas, and endpoints — do not copy this example domain verbatim.

```markdown
## Pet Adoption Portal

You are given a `server.js` file and an in-memory MongoDB database. Your task is to build Node.js APIs using **Express** and **Mongoose** to manage a pet adoption system.

---

## Database

The app uses **`mongodb-memory-server`** for an in-memory MongoDB instance. No external database connection is required.

---

## Pet Schema

Define a **Pet** schema with the following fields:

* **name** (String, required) – The name of the pet.
* **species** (String, required) – The species of the pet (either "dog", "cat", "rabbit", or "bird").
* **breed** (String, required) – The breed of the pet.
* **isAdopted** (Boolean, default: false) – Whether the pet has been adopted or not.
* **listedAt** (Date, default: Date.now) – The timestamp when the pet was listed.

---

## API Endpoints

1. **POST /pets/add-pet** – Add a new pet

    * **Functionality**:
    
      * Accepts the pet's details in the request body.
      * Creates a new pet in the database from the provided request body.
      * Returns the created pet on success with status **201**.

   * **Request Body Example**:
   
    ```
    {
      "name": "Buddy",
      "species": "dog",
      "breed": "Labrador",
      "isAdopted": false
    }
    ```

   * **Response (Success)**:
   
    ```
    {
      "_id": "507f1f77bcf86cd799439011",
      "name": "Buddy",
      "species": "dog",
      "breed": "Labrador",
      "isAdopted": false,
      "listedAt": "2024-01-15T10:30:00.000Z",
      "__v": 0
    }
    ```

---

2. **GET /pets/list** – Retrieve all pets

   * **Functionality**:
      * Returns all pets from the database as a JSON array.
      * Responds with status **200**.

   * **Response (Success)**:
   
    ```
    [
      {
        "_id": "507f1f77bcf86cd799439011",
        "name": "Buddy",
        "species": "dog",
        "breed": "Labrador",
        "isAdopted": false,
        "listedAt": "2026-01-15T10:30:00.000Z",
        "__v": 0
      },
      ...
    ]
    ```

---

## Folder Structure

```
├── models/
│   └── pet.js
├── controllers/
│   └── petController.js
├── routes/
│   └── petRoutes.js
├── db.js
├── server.js
└── package.json
```

---

<MultiLineNote>

* Export the express instance using the default export syntax.
* Follow the exact folder structure and file names as specified to ensure consistency.
* Implement the exact API endpoints mentioned in the description.
* Use `npm install` to install the packages.
* **Pre-filled files (Do NOT modify):**
   * `server.js` – Express app setup, port configuration, and route connection.
   * `db.js` – In-memory MongoDB connection using `mongodb-memory-server`.
   * `package.json` – All required dependencies are already listed; just run `npm install`.
* **Files students must write:**
   * `models/pet.js` – Define the Mongoose Pet schema with all required fields, types, and defaults.
   * `controllers/petController.js` – Handle the **POST /pets/add-pet** and **GET /pets/list** request logic.
   * `routes/petRoutes.js` – Connect the route paths to the controller functions.

Any deviation from the specified paths, endpoints, port, or database name will lead to test case failures.

</MultiLineNote>
```

Rules:
- Replace title, schemas, endpoints, folder tree, and file lists with **this question's** actual generated content.
- If the user provided a title, use it as the `##` heading.
- If no title was provided, choose a clear, domain-appropriate title.
- List every **student file** and every **scaffold file** accurately in `<MultiLineNote>`.
