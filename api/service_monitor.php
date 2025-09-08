<?php
header('Content-Type: application/json');
require_once 'db_connect.php';

// Включение логгирования для отладки
file_put_contents('api.log', date('[Y-m-d H:i:s]') . " Request: " . file_get_contents('php://input') . "\n", FILE_APPEND);

// Проверка метода запроса
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode([
        'success' => false,
        'error' => 'Only POST method is allowed',
        'received_method' => $_SERVER['REQUEST_METHOD']
    ]);
    exit;
}

// Проверка заголовка Content-Type
if (!isset($_SERVER['CONTENT_TYPE']) || stripos($_SERVER['CONTENT_TYPE'], 'application/json') === false) {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'error' => 'Content-Type must be application/json',
        'received_content_type' => $_SERVER['CONTENT_TYPE'] ?? 'Not provided'
    ]);
    exit;
}

// Чтение и декодирование JSON
$input = json_decode(file_get_contents('php://input'), true);
if (json_last_error() !== JSON_ERROR_NONE) {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'error' => 'Invalid JSON: ' . json_last_error_msg(),
        'raw_input' => file_get_contents('php://input')
    ]);
    exit;
}

// Проверка обязательного поля action
if (!isset($input['action'])) {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'error' => 'Missing required field: action',
        'received_data' => $input
    ]);
    exit;
}

// Допустимые действия
$allowed_actions = ['get', 'add', 'update', 'delete', 'get_all_users_services', 'get_down_services'];
if (!in_array($input['action'], $allowed_actions)) {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'error' => 'Invalid action. Allowed: ' . implode(', ', $allowed_actions),
        'received_action' => $input['action']
    ]);
    exit;
}

// Обработка действий
try {
    $mysqli = connectDB();
    
    switch ($input['action']) {
        case 'get':
            // Валидация параметров
            if (empty($input['user_id'])) {
                throw new Exception('Missing required field: user_id');
            }

            $stmt = $mysqli->prepare("SELECT * FROM service_monitor WHERE id = ?");
            $stmt->bind_param("s", $input['user_id']);
            $stmt->execute();
            $result = $stmt->get_result();
            
            if ($result->num_rows === 0) {
                echo json_encode(['success' => true, 'exists' => false]);
                break;
            }
            
            $row = $result->fetch_assoc();
            $services = array_filter([
                $row['user_service'],
                $row['user_service_2'],
                $row['user_service_3']
            ]);
            
            echo json_encode([
                'success' => true,
                'exists' => true,
                'user_service' => $row['user_service'],
                'user_service_2' => $row['user_service_2'],
                'user_service_3' => $row['user_service_3'],
                'services' => array_values($services) // Удаляет null-значения
            ]);
            break;
            
        case 'add':
            // Валидация параметров
            $required = ['user_id', 'username', 'service'];
            foreach ($required as $field) {
                if (empty($input[$field])) {
                    throw new Exception("Missing required field: $field");
                }
            }

            $stmt = $mysqli->prepare("INSERT INTO service_monitor (id, username, user_service) VALUES (?, ?, ?)");
            $stmt->bind_param("sss", $input['user_id'], $input['username'], $input['service']);
            $stmt->execute();
            
            echo json_encode([
                'success' => true,
                'message' => 'Service added',
                'affected_rows' => $stmt->affected_rows
            ]);
            break;
            
        case 'update':
            // Валидация параметров
            $required = ['user_id', 'field', 'service', 'username'];
            foreach ($required as $field) {
                if (empty($input[$field])) {
                    throw new Exception("Missing required field: $field");
                }
            }

            // Проверка допустимых полей для обновления
            $allowed_fields = ['user_service', 'user_service_2', 'user_service_3'];
            if (!in_array($input['field'], $allowed_fields)) {
                throw new Exception("Invalid field. Allowed: " . implode(', ', $allowed_fields));
            }

            $query = "UPDATE service_monitor SET `{$input['field']}` = ?, username = ? WHERE id = ?";
            $stmt = $mysqli->prepare($query);
            $stmt->bind_param("sss", $input['service'], $input['username'], $input['user_id']);
            $stmt->execute();
            
            echo json_encode([
                'success' => true,
                'message' => 'Service updated',
                'affected_rows' => $stmt->affected_rows
            ]);
            break;
            
        case 'delete':
            // Валидация параметров
            $required = ['user_id', 'field'];
            foreach ($required as $field) {
                if (empty($input[$field])) {
                    throw new Exception("Missing required field: $field");
                }
            }

            // Проверка допустимых полей
            $allowed_fields = ['user_service', 'user_service_2', 'user_service_3'];
            if (!in_array($input['field'], $allowed_fields)) {
                throw new Exception("Invalid field. Allowed: " . implode(', ', $allowed_fields));
            }

            $query = "UPDATE service_monitor SET `{$input['field']}` = NULL WHERE id = ?";
            $stmt = $mysqli->prepare($query);
            $stmt->bind_param("s", $input['user_id']);
            $stmt->execute();
            
            echo json_encode([
                'success' => true,
                'message' => 'Service deleted',
                'affected_rows' => $stmt->affected_rows
            ]);
            break;
            
        case 'get_all_users_services':
            $stmt = $mysqli->prepare("SELECT id, username, user_service, user_service_2, user_service_3 FROM service_monitor");
            $stmt->execute();
            $result = $stmt->get_result();
            
            $users = [];
            while ($row = $result->fetch_assoc()) {
                $services = array_filter([
                    $row['user_service'],
                    $row['user_service_2'],
                    $row['user_service_3']
                ]);
                
                if (!empty($services)) {
                    $users[] = [
                        'id' => $row['id'],
                        'username' => $row['username'],
                        'user_service' => $row['user_service'],
                        'user_service_2' => $row['user_service_2'],
                        'user_service_3' => $row['user_service_3']
                    ];
                }
            }
            
            echo json_encode([
                'success' => true,
                'count' => count($users),
                'data' => $users
            ]);
            break;
            
        case 'get_down_services':
            $stmt = $mysqli->prepare("SELECT service_name FROM down_services");
            $stmt->execute();
            $result = $stmt->get_result();
            
            $services = [];
            while ($row = $result->fetch_assoc()) {
                $services[] = $row['service_name'];
            }
            
            echo json_encode([
                'success' => true,
                'services' => $services
            ]);
            break;
            
        default:
            http_response_code(400);
            echo json_encode([
                'success' => false,
                'error' => 'Unknown action',
                'received_action' => $input['action']
            ]);
    }
    
    $mysqli->close();
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => $e->getMessage(),
        'trace' => $e->getTraceAsString()
    ]);
    file_put_contents('api_errors.log', date('[Y-m-d H:i:s]') . " Error: " . $e->getMessage() . "\n", FILE_APPEND);
}
?>