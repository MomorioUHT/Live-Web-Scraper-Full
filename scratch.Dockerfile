FROM node:18-alpine
ARG MY_VAR
RUN node -e "console.log('MY_VAR is', process.env.MY_VAR)"
