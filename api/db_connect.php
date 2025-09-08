<?php
function connectDB() {
    $mysqli = new mysqli('localhost', 'NameDataBase', 'Password', 'DataBase');
    
    if ($mysqli->connect_error) {
        throw new Exception('MySQL error: ' . $mysqli->connect_error);
    }
    
    return $mysqli;
}
?>