
const read = require('readline-sync');

const todos = []; // empty array

function addtodo(todo) {
    todos.push(todo);
    console.log(todo + " added");
}

function seealltodos() {
    if (todos.length === 0) {
        console.log("No todos available.");
    } else {
        for (let todo of todos) {
            console.log(todo);
        }
    }
}

function deletetodo(name) {
    let index = -1;

    for (let i = 0; i < todos.length; i++) {
        if (todos[i] == name) {
            index = i;
            break;
        }
    }

    if (index !== -1) {
        todos.splice(index, 1);
        console.log(name + " deleted");
    } else {
        console.log(name + " not found");
    }
}

while (true) {

    const op = read.question(
        "\n1. Add new todo\n2. See all todos\n3. Remove todo\n4. Exit\nChoose option: "
    );

    switch (Number(op)) {

        case 1:
            let task = read.question("Enter task: ");
            addtodo(task);
            break;

        case 2:
            seealltodos();
            break;

        case 3:
            let name = read.question("Enter todo to delete: ");
            deletetodo(name);
            break;

        case 4:
            console.log("Exiting...");
            process.exit();

        default:
            console.log("Choose correct option");
    }
}

