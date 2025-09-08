<?php
header('Content-Type: application/json');

$mysqli = new mysqli('localhost', 'NameDataBase', 'Password', 'DataBase');

if ($mysqli->connect_error) {
    die(json_encode(['success' => false, 'error' => 'MySQL error: ' . $mysqli->connect_error]));
}

// Начинаем транзакцию
$mysqli->begin_transaction();

try {
    // 1. Очищаем таблицу
    if (!$mysqli->query('TRUNCATE TABLE down_services')) {
        throw new Exception('Clear error: ' . $mysqli->error);
    }

    // 2. Получаем новые данные
    $input = json_decode(file_get_contents('php://input'), true);
    if (!$input || !isset($input['down_services'])) {
        throw new Exception('Invalid input data');
    }

    // 3. Добавляем новые записи
    $stmt = $mysqli->prepare("
        INSERT INTO down_services 
        (service_name, icon_url, 
         reg_1, per_1, reg_2, per_2, reg_3, per_3,
         service_1, percent_1, service_2, percent_2, service_3, percent_3) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ");
    if (!$stmt) {
        throw new Exception('Prepare failed: ' . $mysqli->error);
    }

    $count = 0;
    foreach ($input['down_services'] as $service) {
        // Регионы
        $reg_1 = $reg_2 = $reg_3 = '';
        $per_1 = $per_2 = $per_3 = '';
        
        if (isset($service['regions']) && count($service['regions']) > 0) {
            $reg_1 = $service['regions'][0]['name'] ?? '';
            $per_1 = $service['regions'][0]['percentage'] ?? '';
            
            if (count($service['regions']) > 1) {
                $reg_2 = $service['regions'][1]['name'] ?? '';
                $per_2 = $service['regions'][1]['percentage'] ?? '';
                
                if (count($service['regions']) > 2) {
                    $reg_3 = $service['regions'][2]['name'] ?? '';
                    $per_3 = $service['regions'][2]['percentage'] ?? '';
                }
            }
        }
        
        // Проблемы
        $service_1 = $service_2 = $service_3 = '';
        $percent_1 = $percent_2 = $percent_3 = '';
        
        if (isset($service['problems']) && count($service['problems']) > 0) {
            $service_1 = $service['problems'][0]['name'] ?? '';
            $percent_1 = $service['problems'][0]['percentage'] ?? '';
            
            if (count($service['problems']) > 1) {
                $service_2 = $service['problems'][1]['name'] ?? '';
                $percent_2 = $service['problems'][1]['percentage'] ?? '';
                
                if (count($service['problems']) > 2) {
                    $service_3 = $service['problems'][2]['name'] ?? '';
                    $percent_3 = $service['problems'][2]['percentage'] ?? '';
                }
            }
        }
        
        $stmt->bind_param(
            "ssssssssssssss", 
            $service['name'], 
            $service['icon_url'],
            $reg_1, $per_1, $reg_2, $per_2, $reg_3, $per_3,
            $service_1, $percent_1, $service_2, $percent_2, $service_3, $percent_3
        );
        
        if (!$stmt->execute()) {
            throw new Exception('Execute failed: ' . $stmt->error);
        }
        $count++;
    }

    // Фиксируем транзакцию
    $mysqli->commit();
    
    echo json_encode([
        'success' => true,
        'message' => "Обновлено $count сервисов",
        'count' => $count
    ]);

} catch (Exception $e) {
    // Откатываем при ошибке
    $mysqli->rollback();
    echo json_encode([
        'success' => false,
        'error' => $e->getMessage()
    ]);
} finally {
    $stmt->close();
    $mysqli->close();
}
?>