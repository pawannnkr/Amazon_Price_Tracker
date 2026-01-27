from api.app import app

if __name__ == '__main__':
    print("🚀 Starting Amazon Price Tracker API...")
    print("📡 API will be available at http://localhost:5000")
    print("📚 API Documentation:")
    print("   GET  /api/health - Health check")
    print("   GET  /api/products - Get all products")
    print("   POST /api/products - Add a product")
    print("   DELETE /api/products/<url> - Remove a product")
    print("   POST /api/products/check - Check price for URL")
    print("   POST /api/products/update-all - Update all prices")
    print("   GET  /api/notifications - Get notification settings")
    print("   PUT  /api/notifications - Update notification settings")
    print("   POST /api/notify - Send notification")
    print("\nPress Ctrl+C to stop the server\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
