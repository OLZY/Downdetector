import os
import sys
import time
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import schedule

class DowndetectorMonitor:
    def __init__(self):
        self.base_url = "https://downdetector.su"
        self.api_url = "https://ваш-домен.ру/api/update_db.php"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        })
        #Меняем на рабочие прокси, сделано на случай обхода блокировки сайта downdetector.su
        self.proxies = [
            "http://20.127.145.35:3128",
            "http://57.129.81.201:8080",
            "http://57.129.81.201:8081",
            "http://51.81.245.3:17981",
            "http://23.237.210.82:80",
            "http://57.129.81.201:3128:",
            "http://185.234.65.66:1080",
            "http://54.250.76.76:3128",
            "http://200.174.198.86:8888",
            "http://62.171.179.104:8001"
        ]
        
        self.current_proxy = None
        self.proxy_failures = {}

    def get_random_proxy(self):
        working_proxies = [p for p in self.proxies if self.proxy_failures.get(p, 0) < 2]
        if not working_proxies:
            print("Все прокси не работают, сбрасываем счетчики ошибок")
            self.proxy_failures = {}
            working_proxies = self.proxies.copy()
        
        proxy = random.choice(working_proxies)
        self.current_proxy = proxy
        return {'http': proxy, 'https': proxy}

    def make_request(self, url, method='get', **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                proxies = self.get_random_proxy()
                print(f"Используется прокси: {self.current_proxy}")
                
                if method.lower() == 'get':
                    response = self.session.get(url, proxies=proxies, timeout=10, **kwargs)
                else:
                    response = self.session.post(url, proxies=proxies, timeout=10, **kwargs)
                
                response.raise_for_status()
                return response
                
            except Exception as e:
                print(f"Ошибка с прокси {self.current_proxy}: {str(e)}")
                self.proxy_failures[self.current_proxy] = self.proxy_failures.get(self.current_proxy, 0) + 1
                
                if attempt == max_retries - 1:
                    print("Пробуем запрос без прокси")
                    try:
                        return self.session.get(url, timeout=10, **kwargs)
                    except Exception as e:
                        print(f"Финальная ошибка: {e}")
                        raise

    def parse_service_page(self, url):
        """Парсинг страницы сервиса для получения регионов и проблем"""
        try:
            response = self.make_request(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            data = {
                'regions': [],
                'problems': []
            }
            
            # Парсинг регионов
            histograms = soup.find('div', class_='histograms')
            if histograms:
                regions_section = histograms.find('h2', string=lambda t: 'регионах' in t.lower())
                if regions_section:
                    next_sibling = regions_section.find_next_sibling('p')
                    if next_sibling:
                        labels = next_sibling.find_next_siblings('label')
                        for i, label in enumerate(labels[:3]):  # Берем первые 3 региона
                            a_tag = label.find('a')
                            region_name = a_tag.text if a_tag else label.text.strip()
                            span = label.find('span', class_='region')
                            if span and 'data-pos' in span.attrs:
                                data['regions'].append({
                                    'name': region_name,
                                    'percentage': span['data-pos']
                                })
            
            # Парсинг проблем
            problems_section = histograms.find('h2', string=lambda t: 'неполадки' in t.lower())
            if problems_section:
                next_sibling = problems_section.find_next_sibling('p')
                if next_sibling:
                    labels = next_sibling.find_next_siblings('label')
                    for i, label in enumerate(labels[:3]):  # Берем первые 3 проблемы
                        a_tag = label.find('a')
                        problem_name = a_tag.text if a_tag else label.text.strip()
                        span = label.find('span', class_='cause')
                        if span and 'data-pos' in span.attrs:
                            data['problems'].append({
                                'name': problem_name,
                                'percentage': span['data-pos']
                            })
            
            return data

        except Exception as e:
            print(f"Ошибка парсинга страницы сервиса: {e}")
            return None

    def parse_downdetector(self):
        """Парсинг статуса сервисов"""
        try:
            response = self.make_request(f"{self.base_url}/?nocache={time.time()}")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            services = []
            for card in soup.select('.card.down:not([data-branch])'):
                service_name = card.get('data-service', '').strip()
                if not service_name:
                    continue
                
                img = card.find('img', src=True)
                icon_url = f"{self.base_url}{img['src']}" if img and img['src'].startswith('/icons/') else f"{self.base_url}/img/dummy.svg"
                
                # Получаем ссылку на страницу сервиса
                service_url = f"{self.base_url}{card['href']}" if 'href' in card.attrs else None
                service_data = {
                    "name": service_name,
                    "icon_url": icon_url,
                    "service_url": service_url
                }
                
                # Парсим дополнительную информацию со страницы сервиса
                if service_url:
                    page_data = self.parse_service_page(service_url)
                    if page_data:
                        service_data.update(page_data)
                
                services.append(service_data)
            
            return services

        except Exception as e:
            print(f"Ошибка парсинга: {e}")
            return None

    def update_database(self, services):
        """Отправка данных в БД"""
        try:
            response = self.make_request(
                self.api_url,
                method='post',
                json={"down_services": services}
            )
            result = response.json()
            return result.get('success', False)
        except Exception as e:
            print(f"Ошибка обновления БД: {e}")
            return False

    def monitoring_cycle(self):
        print(f"\n{'='*50}")
        print(f"Проверка в {datetime.now().strftime('%H:%M:%S')}")
        
        services = self.parse_downdetector()
        if services is None:
            print("Ошибка получения данных")
            return
            
        status = self.update_database(services if services else [])
        print(f"Статус: {'Успешно' if status else 'Ошибка'}")
        print(f"Следующая проверка в {(datetime.now() + timedelta(minutes=5)).strftime('%H:%M:%S')}")

    def run(self):
        print("Бот мониторинга запущен")
        print(f"Доступно прокси: {len(self.proxies)}")
        print("="*50)
        
        self.monitoring_cycle()
        schedule.every(5).minutes.do(self.monitoring_cycle)
        
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    bot = DowndetectorMonitor()
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\nБот остановлен")
    except Exception as e:
        print(f"Критическая ошибка: {e}")