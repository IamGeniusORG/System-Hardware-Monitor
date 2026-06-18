import time
import csv
import GPUtil
import psutil
from datetime import datetime

def main():
    csv_filename = "hardware_log.csv"
    
    # Initialize the CSV file with headers if it doesn't exist or we want to overwrite
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            "Timestamp", 
            "GPU ID", 
            "GPU Name", 
            "GPU Load (%)", 
            "GPU Memory Load (%)",
            "GPU Temperature (C)", 
            "CPU Usage (%)", 
            "RAM Usage (%)"
        ])

    print(f"Started logging hardware metrics to {csv_filename}...")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Fetch CPU and RAM metrics
            cpu_usage = psutil.cpu_percent()
            ram_usage = psutil.virtual_memory().percent

            # Fetch GPU metrics
            gpus = GPUtil.getGPUs()
            
            with open(csv_filename, mode='a', newline='') as file:
                writer = csv.writer(file)
                
                if not gpus:
                    # Fallback if no GPU is detected
                    writer.writerow([
                        timestamp, "N/A", "No GPU Found", "N/A", "N/A", "N/A", cpu_usage, ram_usage
                    ])
                else:
                    for gpu in gpus:
                        # gpu.load and gpu.memoryUtil are fractions, multiply by 100 for percentage
                        gpu_load_percent = round(gpu.load * 100, 1)
                        gpu_mem_percent = round(gpu.memoryUtil * 100, 1)
                        gpu_temp = gpu.temperature
                        
                        writer.writerow([
                            timestamp,
                            gpu.id,
                            gpu.name,
                            gpu_load_percent,
                            gpu_mem_percent,
                            gpu_temp,
                            cpu_usage,
                            ram_usage
                        ])
            
            # Wait for 5 seconds before the next iteration
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nLogging stopped by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()
