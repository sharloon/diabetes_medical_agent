"""
启动脚本 - 糖尿病智能诊断助手
"""
import os
import sys

# 设置环境变量
os.environ.setdefault('DASHSCOPE_API_KEY', 'your-api-key')

def main():
    """主启动函数"""
    print("=" * 60)
    print("  糖尿病智能诊断助手")
    print("  基于RAG和智能体技术的专家级医疗决策支持系统")
    print("=" * 60)
    print()
    
    # 检查依赖
    try:
        import flask
        import openai
        import pandas
        import pymysql
        print("✓ 核心依赖检查通过")
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        sys.exit(1)
    
    # 检查API密钥
    api_key = os.getenv('DASHSCOPE_API_KEY')
    if not api_key or api_key == 'your-api-key':
        print("⚠ 警告: 请设置环境变量 DASHSCOPE_API_KEY")
        print("  可以通过以下方式设置:")
        print("  - Windows: set DASHSCOPE_API_KEY=your-key")
        print("  - Linux/Mac: export DASHSCOPE_API_KEY=your-key")
        print()
    
    # 导入并启动应用
    from app import app, init_app
    
    init_app()
    
    print()
    print("=" * 60)
    print("  应用启动成功!")
    print("  访问地址: http://localhost:5000")
    print("=" * 60)
    print()
    
    app.run(host='0.0.0.0', port=5000, debug=True)


if __name__ == '__main__':
    main()

