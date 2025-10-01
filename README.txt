# To run
Local:  uvicorn app.main:app --reload
# Docker requires sharing of the local /tmp files. See fund_xl.rb
Docker: docker run -p 8000:80 -v /tmp:/tmp thimmaiah/xirr_py

# To build
 docker build -t thimmaiah/xirr_py .
 docker push thimmaiah/xirr_py