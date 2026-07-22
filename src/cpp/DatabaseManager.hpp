#ifndef DATABASE_MANAGER_HPP
#define DATABASE_MANAGER_HPP

#include <iostream>
#include <string>
#include <libpq-fe.h>

class DatabaseManager {
private:
    PGconn* conn;

public:
    // Constructor: Veritabanı bağlantı dizesini alır (örn: "host=localhost port=5432 dbname=bist_lob user=postgres password=sifreniz")
    DatabaseManager(const std::string& conninfo) {
        conn = PQconnectdb(conninfo.c_str());
        if (PQstatus(conn) != CONNECTION_OK) {
            std::cerr << "Veritabani baglanti hatasi: " << PQerrorMessage(conn) << std::endl;
        } else {
            std::cout << "PostgreSQL veritabanina basariyla baglanildi!" << std::endl;
        }
    }

    // Destructor: Bağlantıyı güvenli bir şekilde kapatır
    ~DatabaseManager() {
        if (conn) {
            PQfinish(conn);
        }
    }

    // Bağlantı durumunu kontrol eder
    bool isConnected() const {
        return conn && PQstatus(conn) == CONNECTION_OK;
    }

    // SQL komutlarını (INSERT, CREATE TABLE vb.) çalıştırmak için
    void executeQuery(const std::string& query) {
        if (!isConnected()) {
            std::cerr << "Veritabani aktif degil, sorgu calistirilamadi." << std::endl;
            return;
        }
        
        PGresult* res = PQexec(conn, query.c_str());
        ExecStatusType status = PQresultStatus(res);
        
        if (status != PGRES_COMMAND_OK && status != PGRES_TUPLES_OK) {
            std::cerr << "Sorgu hatasi: " << PQerrorMessage(conn) << std::endl;
        }
        
        PQclear(res);
    }
};

#endif