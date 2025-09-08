<?php
header('Content-Type: application/json');

$mysqli = new mysqli('localhost', 'NameDataBase', 'Password', 'DataBase');

if ($mysqli->connect_error) {
    die(json_encode(['success' => false, 'error' => 'MySQL error: ' . $mysqli->connect_error]));
}

$result = $mysqli->query('
    SELECT service_name, icon_url, timestamp,
           reg_1, per_1, reg_2, per_2, reg_3, per_3,
           service_1, percent_1, service_2, percent_2, service_3, percent_3
    FROM down_services 
    ORDER BY timestamp DESC 
    LIMIT 10
');

if (!$result) {
    die(json_encode(['success' => false, 'error' => 'Query error: ' . $mysqli->error]));
}

$services = [];
while ($row = $result->fetch_assoc()) {
    $services[] = $row;
}

echo json_encode(['success' => true, 'services' => $services]);
$mysqli->close();
?>