### Intento 1: PowerShell heredoc con `python - << 'PY'`

```text
En lnea: 1 Carter: 203
+ ... tall --upgrade pip; pip install -r requirements.txt; python - << 'PY'
+                                                                    ~
Falta la especificacin de archivo despus del operador de redireccin.
En lnea: 1 Carter: 202
+ ... tall --upgrade pip; pip install -r requirements.txt; python - << 'PY'
+                                                                   ~
El operador '<' est reservado para uso futuro.
En lnea: 1 Carter: 203
+ ... tall --upgrade pip; pip install -r requirements.txt; python - << 'PY'
+                                                                    ~
El operador '<' est reservado para uso futuro.
En lnea: 2 Carter: 1
+ from data.synthetic_generator import generate_transactions
+ ~~~~
La palabra clave 'from' no se admite en esta versin del idioma.
En lnea: 5 Carter: 35
+ df = generate_transactions(seed=42, num_transactions=100)
+                                   ~
Falta un argumento en la lista de parmetros.
En lnea: 6 Carter: 54
+ df.to_csv('data/sample_data/transactions_sample.csv', index=False)
+                                                      ~
Falta una expresin despus de ','.
En lnea: 6 Carter: 55
+ df.to_csv('data/sample_data/transactions_sample.csv', index=False)
+                                                       ~~~~~~~~~~~
Token 'index=False' inesperado en la expresin o la instruccin.
En lnea: 6 Carter: 54
+ df.to_csv('data/sample_data/transactions_sample.csv', index=False)
+                                                      ~
Falta el parntesis de cierre ')' en la expresin.
En lnea: 6 Carter: 66
+ df.to_csv('data/sample_data/transactions_sample.csv', index=False)
+                                                                  ~
Token ')' inesperado en la expresin o la instruccin.
En lnea: 7 Carter: 56
+ print('WROTE:data/sample_data/transactions_sample.csv', len(df))
+                                                        ~
Falta una expresin despus de ','.
No se notificaron todos los errores de anlisis. Corrija los errores notificados e intntelo de nuevo.
    + CategoryInfo          : ParserError: (:) [], ParentContainsErrorRecordException
    + FullyQualifiedErrorId : MissingFileSpecification
```

---

### Intento 2: Python/Pip no reconocidos en PowerShell

```text
python : El trmino 'python' no se reconoce como nombre de un cmdlet, funcin, archivo de script o programa 
ejecutable. Compruebe si escribi correctamente el nombre o, si incluy una ruta de acceso, compruebe que dicha ruta 
es correcta e intntelo de nuevo.
En lnea: 1 Carter: 73
+ ... fraud-detection-graphs'; if (-not (Test-Path .venv)) { python -m venv ...
+                                                            ~~~~~~
    + CategoryInfo          : ObjectNotFound: (python:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
.\.venv\Scripts\Activate.ps1 : El trmino '.\.venv\Scripts\Activate.ps1' no se reconoce como nombre de un cmdlet, 
funcin, archivo de script o programa ejecutable. Compruebe si escribi correctamente el nombre o, si incluy una ruta 
de acceso, compruebe que dicha ruta es correcta e intntelo de nuevo.
En lnea: 1 Carter: 97
+ ... venv)) { python -m venv .venv }; .\.venv\Scripts\Activate.ps1; python ...
+                                      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (.:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
python : El trmino 'python' no se reconoce como nombre de un cmdlet, funcin, archivo de script o programa 
ejecutable. Compruebe si escribi correctamente el nombre o, si incluy una ruta de acceso, compruebe que dicha ruta 
es correcta e intntelo de nuevo.
En lnea: 1 Carter: 127
+ ...  python -m venv .venv }; .\.venv\Scripts\Activate.ps1; python -m pip  ...
+                                                            ~~~~~~
    + CategoryInfo          : ObjectNotFound: (python:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
pip : El trmino 'pip' no se reconoce como nombre de un cmdlet, funcin, archivo de script o programa ejecutable. 
Compruebe si escribi correctamente el nombre o, si incluy una ruta de acceso, compruebe que dicha ruta es correcta e 
intntelo de nuevo.
En lnea: 1 Carter: 164
+ ... cripts\Activate.ps1; python -m pip install --upgrade pip; pip install ...
+                                                               ~~~
    + CategoryInfo          : ObjectNotFound: (pip:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
 
python : El trmino 'python' no se reconoce como nombre de un cmdlet, funcin, archivo de script o programa 
ejecutable. Compruebe si escribi correctamente el nombre o, si incluy una ruta de acceso, compruebe que dicha ruta 
es correcta e intntelo de nuevo.
En lnea: 1 Carter: 197
+ ... nstall --upgrade pip; pip install -r requirements.txt; python example ...
+                                                            ~~~~~~
    + CategoryInfo          : ObjectNotFound: (python:String) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
```
